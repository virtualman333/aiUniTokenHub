from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from apps.users.models import User, APIKey, UsageLog
from apps.api_proxy.models import APIEndpoint, APICategory


class DashboardViewSet(viewsets.GenericViewSet):
    """仪表盘"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """总览数据"""
        is_admin = request.user.role == 'admin'
        
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        
        base_qs = UsageLog.objects.all() if is_admin else UsageLog.objects.filter(user=request.user)
        base_qs_today = base_qs.filter(created_at__gte=today_start)
        
        data = {
            'total_requests': base_qs.count(),
            'today_requests': base_qs_today.count(),
            'total_users': User.objects.count() if is_admin else 1,
            'total_apis': APIEndpoint.objects.count() if is_admin else APIEndpoint.objects.filter(is_active=True).count(),
        }
        
        # 计算成功率
        total = base_qs.count()
        success = base_qs.filter(status_code__gte=200, status_code__lt=300).count()
        data['success_rate'] = round(success / total * 100, 2) if total > 0 else 100
        
        # 平均响应时间
        avg_time = base_qs.aggregate(avg=Avg('response_time'))['avg']
        data['avg_response_time'] = round(avg_time, 2) if avg_time else 0
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def request_stats(self, request):
        """请求统计"""
        is_admin = request.user.role == 'admin'
        days = int(request.query_params.get('days', 7))
        
        stats = []
        for i in range(days):
            date = timezone.now().date() - timedelta(days=i)
            start = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()))
            end = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.max.time()))
            
            qs = UsageLog.objects.filter(created_at__gte=start, created_at__lte=end)
            if not is_admin:
                qs = qs.filter(user=request.user)
            
            stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': qs.count(),
                'avg_time': round(qs.aggregate(avg=Avg('response_time'))['avg'] or 0, 2),
            })
        
        return Response(stats[::-1])
    
    @action(detail=False, methods=['get'])
    def top_apis(self, request):
        """热门API"""
        is_admin = request.user.role == 'admin'
        limit = int(request.query_params.get('limit', 10))
        
        qs = UsageLog.objects.values('endpoint').annotate(count=Count('id')).order_by('-count')[:limit]
        result = []
        for item in qs:
            endpoint = APIEndpoint.objects.filter(path=item['endpoint']).first()
            if endpoint:
                result.append({
                    'name': endpoint.name,
                    'path': endpoint.path,
                    'count': item['count'],
                })
        
        return Response(result)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def admin_stats(self, request):
        """管理员统计"""
        data = {
            'users': {
                'total': User.objects.count(),
                'active': User.objects.filter(is_active=True).count(),
                'new_today': User.objects.filter(date_joined__date=timezone.now().date()).count(),
            },
            'api_keys': {
                'total': APIKey.objects.count(),
                'active': APIKey.objects.filter(is_active=True).count(),
            },
            'apis': {
                'total': APIEndpoint.objects.count(),
                'active': APIEndpoint.objects.filter(is_active=True).count(),
                'categories': APICategory.objects.count(),
            },
        }
        return Response(data)
