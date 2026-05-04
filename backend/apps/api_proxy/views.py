import json
import time
import httpx
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.conf import settings
from django.core.cache import cache
from .models import APICategory, APIEndpoint, APIAccessLog
from .serializers import (
    APICategorySerializer, APIEndpointSerializer,
    ProxyRequestSerializer, APIAccessLogSerializer
)
from apps.users.models import APIKey, UsageLog


class APICategoryViewSet(viewsets.ModelViewSet):
    """API分类"""
    queryset = APICategory.objects.filter(is_active=True)
    serializer_class = APICategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            return [AllowAny()]
        return [IsAdminUser()]


class APIEndpointViewSet(viewsets.ModelViewSet):
    """API端点"""
    queryset = APIEndpoint.objects.filter(is_active=True)
    serializer_class = APIEndpointSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            return [AllowAny()]
        return [IsAdminUser()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def proxy(self, request, pk=None):
        """API代理转发"""
        endpoint = self.get_object()
        serializer = ProxyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 验证API Key（如果需要）
        api_key = None
        user = None
        if not endpoint.is_public:
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return Response({'error': '需要API Key'}, status=status.HTTP_401_UNAUTHORIZED)
            
            api_key_str = auth_header.split(' ')[1]
            try:
                api_key = APIKey.objects.get(key=api_key_str, is_active=True)
                if api_key.is_expired:
                    return Response({'error': 'API Key已过期'}, status=status.HTTP_401_UNAUTHORIZED)
                user = api_key.user
            except APIKey.DoesNotExist:
                return Response({'error': '无效的API Key'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # 速率限制检查
        cache_key = f"rate_limit:{api_key.key if api_key else request.ip_address}:{endpoint.id}"
        current = cache.get(cache_key, 0)
        limit = api_key.rate_limit if api_key else endpoint.rate_limit
        if current >= limit:
            return Response({'error': '请求过于频繁'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        cache.set(cache_key, current + 1, 60)
        
        # 记录使用日志
        start_time = time.time()
        log = UsageLog.objects.create(
            user=user,
            api_key=api_key,
            method=serializer.validated_data.get('method', endpoint.method),
            endpoint=endpoint.path,
        )
        
        try:
            # 构建请求
            headers = {**endpoint.headers, **serializer.validated_data.get('headers', {})}
            params = {**endpoint.parameters, **serializer.validated_data.get('params', {})}
            data = serializer.validated_data.get('data')
            
            # 发送请求
            with httpx.Client(timeout=endpoint.timeout) as client:
                method = serializer.validated_data.get('method', endpoint.method).lower()
                response = client.request(
                    method=method,
                    url=endpoint.target_url,
                    headers=headers,
                    params=params,
                    json=data if data else None,
                )
            
            response_time = int((time.time() - start_time) * 1000)
            
            # 更新日志
            log.response_body = response.text[:5000]
            log.status_code = response.status_code
            log.response_time = response_time
            log.save()
            
            return Response({
                'success': True,
                'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                'status': response.status_code,
                'response_time': response_time,
            })
            
        except httpx.TimeoutException:
            log.error_message = '请求超时'
            log.status_code = 504
            log.save()
            return Response({'error': '请求超时'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except Exception as e:
            log.error_message = str(e)
            log.status_code = 500
            log.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProxyAccessViewSet(viewsets.GenericViewSet):
    """代理访问"""
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get', 'post', 'put', 'delete', 'patch'])
    def forward(self, request):
        """通用代理转发"""
        path = request.data.get('path') or request.query_params.get('path')
        target_url = request.data.get('target_url') or request.query_params.get('target_url')
        
        if not path or not target_url:
            return Response({'error': '缺少path或target_url参数'}, status=status.HTTP_400_BAD_REQUEST)
        
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
            
            return Response({
                'success': True,
                'data': response.json() if 'application/json' in response.headers.get('content-type', '') else response.text,
                'status': response.status_code,
                'response_time': response_time,
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
