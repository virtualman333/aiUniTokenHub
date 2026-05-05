import json
import time
import httpx
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from .models import APIAccessLog
from .serializers import ProxyRequestSerializer, APIAccessLogSerializer, AccessLogStatSerializer
from apps.users.models import APIKey, UsageLog
from apps.utils.response import APIResponse


class ProxyAccessViewSet(viewsets.GenericViewSet):
    """代理访问"""
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get', 'post', 'put', 'delete', 'patch'])
    def forward(self, request):
        """通用代理转发"""
        path = request.data.get('path') or request.query_params.get('path')
        target_url = request.data.get('target_url') or request.query_params.get('target_url')
        
        if not path or not target_url:
            return APIResponse.error('缺少path或target_url参数', 400)
        
        start_time = time.time()
        
        try:
            with httpx.Client(timeout=30) as client:
                response = client.request(
                    method=request.method,
                    url=target_url,
                    headers=dict(request.headers),
                    params=request.query_params,
                    json=request.data if request.data else None,
                )
            
            response_time = int((time.time() - start_time) * 1000)
            
            return APIResponse.success({
                'data': response.json() if 'application/json' in response.headers.get('content-type', '') else response.text,
                'status': response.status_code,
                'response_time': response_time,
            }, '请求成功')
            
        except Exception as e:
            return APIResponse.error(str(e), 500)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def access_logs(self, request):
        """访问日志列表"""
        queryset = APIAccessLog.objects.select_related('user', 'api_key').all()
        
        # 按路径筛选
        path = request.query_params.get('path')
        if path:
            queryset = queryset.filter(path__icontains=path)
        
        # 按请求方法筛选
        method = request.query_params.get('method')
        if method:
            queryset = queryset.filter(method=method.upper())
        
        # 按用户名筛选
        username = request.query_params.get('username')
        if username:
            queryset = queryset.filter(user__username__icontains=username)
        
        # 按API Key筛选
        api_key_id = request.query_params.get('api_key_id')
        if api_key_id:
            queryset = queryset.filter(api_key_id=int(api_key_id))
        
        # 按状态码范围筛选
        status_gte = request.query_params.get('status_gte')
        status_lt = request.query_params.get('status_lt')
        if status_gte and status_lt:
            queryset = queryset.filter(response_status__gte=int(status_gte), response_status__lt=int(status_lt))
        
        # 按成功/失败筛选
        success = request.query_params.get('success')
        if success == 'true':
            queryset = queryset.filter(response_status__gte=200, response_status__lt=400)
        elif success == 'false':
            queryset = queryset.filter(Q(response_status__gte=400) | Q(response_status=0))
        
        # 按响应时间筛选
        response_time_gte = request.query_params.get('response_time_gte')
        response_time_lt = request.query_params.get('response_time_lt')
        if response_time_gte:
            queryset = queryset.filter(response_time__gte=int(response_time_gte))
        if response_time_lt:
            queryset = queryset.filter(response_time__lt=int(response_time_lt))
        
        # 按IP地址筛选
        ip_address = request.query_params.get('ip_address')
        if ip_address:
            queryset = queryset.filter(ip_address__icontains=ip_address)
        
        # 按时间范围筛选
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        queryset = queryset.order_by('-created_at')
        
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        logs = queryset[start:end]
        
        serializer = APIAccessLogSerializer(logs, many=True)
        return APIResponse.paginated(serializer.data, total, page, page_size, '获取成功')
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def access_stats(self, request):
        """访问统计"""
        days = int(request.query_params.get('days', 7))
        days = min(days, 30)  # 最多30天
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # 按日期分组统计
        from django.db.models.functions import TruncDate
        stats = APIAccessLog.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total_count=Count('id'),
            success_count=Count('id', filter=Q(response_status__gte=200, response_status__lt=400)),
            error_count=Count('id', filter=Q(response_status__gte=400)),
            avg_response_time=Avg('response_time')
        ).order_by('date')
        
        serializer = AccessLogStatSerializer(stats, many=True)
        
        # 总览统计
        total_logs = APIAccessLog.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        overview = {
            'total_count': total_logs.count(),
            'success_count': total_logs.filter(response_status__gte=200, response_status__lt=400).count(),
            'error_count': total_logs.filter(response_status__gte=400).count(),
            'avg_response_time': total_logs.aggregate(avg=Avg('response_time'))['avg'] or 0,
            'max_response_time': total_logs.order_by('-response_time').first().response_time if total_logs.exists() else 0,
        }
        
        # 按用户统计
        user_stats = APIAccessLog.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).select_related('user').values(
            'user__username'
        ).annotate(
            count=Count('id'),
            avg_time=Avg('response_time')
        ).order_by('-count')[:10]
        
        # 按状态码分布
        status_distribution = APIAccessLog.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).values('response_status').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return APIResponse.success({
            'overview': overview,
            'daily_stats': serializer.data,
            'user_stats': list(user_stats),
            'status_distribution': list(status_distribution),
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def access_log_detail(self, request, pk=None):
        """访问日志详情"""
        try:
            log = APIAccessLog.objects.select_related('user', 'api_key').get(pk=pk)
        except APIAccessLog.DoesNotExist:
            return APIResponse.error('日志不存在', 404)
        
        serializer = APIAccessLogSerializer(log)
        return APIResponse.success(serializer.data)
