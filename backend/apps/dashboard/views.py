from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.db import models
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from apps.users.models import User, APIKey, UsageLog, Bill
from apps.users.serializers import AdminUserSerializer
from apps.api_proxy.models import APIAccessLog
from apps.api_proxy.serializers import APIAccessLogSerializer
from apps.ai_models.models import AIModel, ModelProvider
from apps.utils.response import APIResponse


class AdminDashboardViewSet(viewsets.GenericViewSet):
    """管理端仪表盘"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_permissions(self):
        if self.action in ['list_users', 'retrieve_user']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated(), IsAdminUser()]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """总览数据"""
        today = timezone.now().date()
        month_start = timezone.make_aware(timezone.datetime.combine(today.replace(day=1), timezone.datetime.min.time()))
        
        data = {
            'total_users': User.objects.count(),
            'total_apis': AIModel.objects.count(),
            'total_providers': ModelProvider.objects.count(),
            'total_models': AIModel.objects.count(),
            'total_requests': UsageLog.objects.count(),
            'monthly_cost': float(Bill.objects.filter(
                created_at__gte=month_start,
                type='consume'
            ).aggregate(total=Sum('amount'))['total'] or 0),
        }
        
        return APIResponse.success(data, '获取成功')
    
    @action(detail=False, methods=['get'])
    def trend(self, request):
        """请求趋势"""
        days = int(request.query_params.get('days', 7))
        
        stats = []
        for i in range(days - 1, -1, -1):
            date = timezone.now().date() - timedelta(days=i)
            start = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()))
            end = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.max.time()))
            
            count = UsageLog.objects.filter(created_at__gte=start, created_at__lte=end).count()
            stats.append({
                'date': date.strftime('%m-%d'),
                'count': count
            })
        
        return APIResponse.success(stats, '获取成功')
    
    @action(detail=False, methods=['get'])
    def distribution(self, request):
        """API调用分布"""
        top_apis = UsageLog.objects.values('endpoint').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        result = []
        total = sum(item['count'] for item in top_apis) or 1
        for item in top_apis:
            result.append({
                'name': item['endpoint'],
                'value': item['count'],
                'percent': round(item['count'] / total * 100, 1)
            })
        
        return APIResponse.success(result, '获取成功')
    
    def list_users(self, request):
        """获取用户列表"""
        queryset = User.objects.all().order_by('-created_at')
        
        # 搜索过滤
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(username__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(phone__icontains=search)
            )
        
        # 角色过滤
        role = request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # 状态过滤
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # 分页
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        users = queryset[start:end]
        serializer = AdminUserSerializer(users, many=True)
        
        return APIResponse.paginated(serializer.data, total, page, page_size, '获取成功')
    
    def retrieve_user(self, request, pk=None):
        """获取单个用户"""
        try:
            user = User.objects.get(pk=pk)
            serializer = AdminUserSerializer(user)
            return APIResponse.success(serializer.data, '获取成功')
        except User.DoesNotExist:
            return APIResponse.error('用户不存在', 404)
    
    def partial_update_user(self, request, pk=None):
        """更新用户"""
        try:
            user = User.objects.get(pk=pk)
            serializer = AdminUserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return APIResponse.success(serializer.data, '更新成功')
            return APIResponse.error(str(serializer.errors), 400)
        except User.DoesNotExist:
            return APIResponse.error('用户不存在', 404)
    
    @action(detail=True, methods=['patch'], url_path='balance')
    def adjust_balance(self, request, pk=None):
        """调整用户余额"""
        try:
            user = User.objects.get(pk=pk)
            amount = request.data.get('amount', 0)
            note = request.data.get('note', '')
            
            user.balance += Decimal(str(amount))
            user.save()
            
            return APIResponse.success({
                'balance': user.balance,
                'message': f'余额已{"增加" if amount >= 0 else "减少"} {abs(amount)} 元'
            }, '调整成功')
        except User.DoesNotExist:
            return APIResponse.error('用户不存在', 404)
        except Exception as e:
            return APIResponse.error(str(e), 400)
    
    @action(detail=True, methods=['post'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        """切换用户状态"""
        try:
            user = User.objects.get(pk=pk)
            user.is_active = not user.is_active
            user.save()
            
            return APIResponse.success({
                'is_active': user.is_active,
                'message': f'用户已{"启用" if user.is_active else "禁用"}'
            }, '操作成功')
        except User.DoesNotExist:
            return APIResponse.error('用户不存在', 404)


class UserDashboardViewSet(viewsets.GenericViewSet):
    """用户端仪表盘"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """用户概览数据"""
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        
        # 获取当前用户的请求日志
        user_logs = APIAccessLog.objects.filter(user=request.user)
        today_logs = user_logs.filter(created_at__gte=today_start)
        
        # 计算统计数据
        total_requests = user_logs.count()
        today_requests = today_logs.count()
        
        # 计算成功率
        success_count = user_logs.filter(
            response_status__gte=200, 
            response_status__lt=300
        ).count()
        success_rate = round(success_count / total_requests * 100, 1) if total_requests > 0 else 100
        
        # 计算平均响应时间
        avg_response = user_logs.filter(
            response_time__gt=0
        ).aggregate(avg=Avg('response_time'))['avg']
        avg_response_time = round(avg_response) if avg_response else 0
        
        data = {
            'total_requests': total_requests,
            'today_requests': today_requests,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time
        }
        
        return APIResponse.success(data, '获取成功')
    
    @action(detail=False, methods=['get'])
    def top_apis(self, request):
        """热门API"""
        limit = int(request.query_params.get('limit', 5))
        
        # 按路径统计调用次数
        top_apis = APIAccessLog.objects.filter(
            user=request.user
        ).values('path').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]
        
        result = [
            {'name': item['path'], 'count': item['count']}
            for item in top_apis
        ]
        
        return APIResponse.success(result, '获取成功')
    
    @action(detail=False, methods=['get'])
    def request_stats(self, request):
        """请求统计（趋势）"""
        days = int(request.query_params.get('days', 7))
        days = min(days, 30)  # 最多30天
        
        today = timezone.now().date()
        
        # 按日期分组统计
        stats = []
        for i in range(days - 1, -1, -1):
            date = today - timedelta(days=i)
            date_start = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()))
            date_end = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.max.time()))
            
            day_logs = APIAccessLog.objects.filter(
                user=request.user,
                created_at__gte=date_start,
                created_at__lte=date_end
            )
            
            stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'requests': day_logs.count(),
                'success': day_logs.filter(
                    response_status__gte=200,
                    response_status__lt=300
                ).count(),
                'failed': day_logs.filter(
                    Q(response_status__gte=400) | Q(response_status=0)
                ).count()
            })
        
        return APIResponse.success(stats, '获取成功')
