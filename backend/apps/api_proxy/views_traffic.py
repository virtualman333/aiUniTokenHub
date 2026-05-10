"""
流量分析相关的API视图
"""
import datetime
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncHour, TruncDay
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import viewsets
from .models import APIAccessLog
from apps.ai_models.models import AIModel
from apps.users.models import User
from apps.utils.response import APIResponse


class TrafficAnalysisViewSet(viewsets.ViewSet):
    """流量分析API"""
    permission_classes = [IsAdminUser]
    
    def _get_time_filter(self, request):
        """构建时间过滤条件"""
        time_range = request.query_params.get('time_range', 'today')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        now = timezone.now()
        time_filter = Q()
        
        if time_range == 'today':
            time_filter = Q(created_at__date=now.date())
        elif time_range == 'yesterday':
            yesterday = now.date() - datetime.timedelta(days=1)
            time_filter = Q(created_at__date=yesterday)
        elif time_range == '7days':
            seven_days_ago = now - datetime.timedelta(days=7)
            time_filter = Q(created_at__gte=seven_days_ago)
        elif time_range == '30days':
            thirty_days_ago = now - datetime.timedelta(days=30)
            time_filter = Q(created_at__gte=thirty_days_ago)
        elif time_range == 'custom' and start_date and end_date:
            time_filter = Q(created_at__date__gte=start_date, created_at__date__lte=end_date)
        
        return time_filter
    
    def _get_base_queryset(self, request):
        """获取基础查询集"""
        time_filter = self._get_time_filter(request)
        return APIAccessLog.objects.filter(time_filter)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取统计数据"""
        queryset = self._get_base_queryset(request)
        
        total_requests = queryset.count()
        success_requests = queryset.filter(
            Q(response_status__gte=200) & Q(response_status__lt=300)
        ).count()
        failed_requests = total_requests - success_requests
        
        success_rate = round((success_requests / total_requests * 100) if total_requests > 0 else 0, 2)
        
        avg_response_time = queryset.aggregate(avg_time=Avg('response_time'))['avg_time'] or 0
        avg_response_time = round(avg_response_time, 2)
        
        active_users = queryset.values('user').distinct().count()
        
        return APIResponse.success({
            'totalRequests': total_requests,
            'successRate': success_rate,
            'avgResponseTime': avg_response_time,
            'activeUsers': active_users,
            'failedRequests': failed_requests,
        })
    
    @action(detail=False, methods=['get'])
    def trend(self, request):
        """获取请求趋势数据"""
        queryset = self._get_base_queryset(request)
        time_range = request.query_params.get('time_range', 'today')
        
        # 根据时间范围决定分组粒度
        if time_range == 'today' or time_range == 'yesterday':
            # 按小时分组
            data = queryset.annotate(hour=TruncHour('created_at')).values('hour').annotate(
                total=Count('id'),
                success=Count('id', filter=Q(response_status__gte=200, response_status__lt=300)),
                failed=Count('id', filter=Q(response_status__gte=400) | Q(response_status=0))
            ).order_by('hour')
            
            labels = [item['hour'].strftime('%Y-%m-%d %H:00') if item['hour'] else '' for item in data]
            total = [item['total'] for item in data]
            success = [item['success'] for item in data]
            failed = [item['failed'] for item in data]
        else:
            # 按天分组
            data = queryset.annotate(day=TruncDay('created_at')).values('day').annotate(
                total=Count('id'),
                success=Count('id', filter=Q(response_status__gte=200, response_status__lt=300)),
                failed=Count('id', filter=Q(response_status__gte=400) | Q(response_status=0))
            ).order_by('day')
            
            labels = [item['day'].strftime('%Y-%m-%d') if item['day'] else '' for item in data]
            total = [item['total'] for item in data]
            success = [item['success'] for item in data]
            failed = [item['failed'] for item in data]
        
        return APIResponse.success({
            'labels': labels,
            'total': total,
            'success': success,
            'failed': failed,
        })
    
    @action(detail=False, methods=['get'])
    def status_distribution(self, request):
        """获取状态码分布"""
        queryset = self._get_base_queryset(request)
        
        # 按状态码分组
        status_data = queryset.values('response_status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 转换为饼图数据格式
        colors = {
            2: '#67c23a',  # 2xx 成功
            3: '#409eff',  # 3xx 重定向
            4: '#e6a23c',  # 4xx 客户端错误
            5: '#f56c6c',  # 5xx 服务端错误
            0: '#909399',  # 0 未知
        }
        
        data = []
        for item in status_data:
            status = item['response_status']
            status_prefix = status // 100 if status > 0 else 0
            
            if status_prefix == 2:
                name = f'{status} 成功'
            elif status_prefix == 3:
                name = f'{status} 重定向'
            elif status_prefix == 4:
                name = f'{status} 客户端错误'
            elif status_prefix == 5:
                name = f'{status} 服务端错误'
            else:
                name = f'{status} 未知'
            
            data.append({
                'name': name,
                'value': item['count'],
                'itemStyle': {'color': colors.get(status_prefix, '#909399')}
            })
        
        return APIResponse.success(data)
    
    @action(detail=False, methods=['get'])
    def model_distribution(self, request):
        """获取模型调用分布"""
        queryset = self._get_base_queryset(request)
        
        # 按模型分组
        model_data = queryset.filter(model__isnull=False).values(
            'model__name', 'model__code'
        ).annotate(
            count=Count('id'),
            avg_response_time=Avg('response_time')
        ).order_by('-count')[:10]
        
        # 转换为饼图数据格式
        data = []
        for item in model_data:
            data.append({
                'name': item['model__name'] or item['model__code'],
                'value': item['count'],
            })
        
        return APIResponse.success(data)
    
    @action(detail=False, methods=['get'])
    def response_time_distribution(self, request):
        """获取响应时间分布"""
        queryset = self._get_base_queryset(request)
        
        # 定义响应时间区间
        ranges = [
            (0, 100, '0-100ms'),
            (100, 500, '100-500ms'),
            (500, 1000, '500-1000ms'),
            (1000, 3000, '1-3s'),
            (3000, 5000, '3-5s'),
            (5000, 10000, '5-10s'),
            (10000, 999999, '10s以上'),
        ]
        
        data = []
        labels = []
        
        for min_val, max_val, label in ranges:
            count = queryset.filter(
                response_time__gte=min_val,
                response_time__lt=max_val
            ).count()
            labels.append(label)
            data.append(count)
        
        return APIResponse.success({
            'labels': labels,
            'data': data,
        })
    
    @action(detail=False, methods=['get'])
    def top(self, request):
        """获取TOP数据"""
        queryset = self._get_base_queryset(request)
        
        # 热门模型TOP10
        top_models = queryset.filter(model__isnull=False).values(
            'model__name', 'model__code'
        ).annotate(
            request_count=Count('id'),
            avg_response_time=Avg('response_time')
        ).order_by('-request_count')[:10]
        
        top_models_list = []
        for item in top_models:
            top_models_list.append({
                'model_name': item['model__name'] or item['model__code'],
                'request_count': item['request_count'],
                'avg_response_time': round(item['avg_response_time'] or 0, 2),
            })
        
        # 活跃用户TOP10
        top_users = queryset.filter(user__isnull=False).values(
            'user__username', 'user__id'
        ).annotate(
            request_count=Count('id'),
            total_tokens=Avg('total_tokens')
        ).order_by('-request_count')[:10]
        
        top_users_list = []
        for item in top_users:
            top_users_list.append({
                'username': item['user__username'],
                'request_count': item['request_count'],
                'total_tokens': round(item['total_tokens'] or 0),
            })
        
        return APIResponse.success({
            'models': top_models_list,
            'users': top_users_list,
        })
