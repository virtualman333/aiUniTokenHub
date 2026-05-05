import json
import time
import httpx
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count
from .models import APIAccessLog
from .serializers import ProxyRequestSerializer, APIAccessLogSerializer
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
        """访问日志"""
        queryset = APIAccessLog.objects.select_related('user', 'endpoint').all()
        
        path = request.query_params.get('path')
        if path:
            queryset = queryset.filter(path__icontains=path)
        
        method = request.query_params.get('method')
        if method:
            queryset = queryset.filter(method=method.upper())
        
        username = request.query_params.get('username')
        if username:
            queryset = queryset.filter(user__username__icontains=username)
        
        status_gte = request.query_params.get('status_gte')
        status_lt = request.query_params.get('status_lt')
        if status_gte and status_lt:
            queryset = queryset.filter(response_status__gte=int(status_gte), response_status__lt=int(status_lt))
        
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
