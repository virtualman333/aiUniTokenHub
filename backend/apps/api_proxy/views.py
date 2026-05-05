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
from .models import APICategory, APIEndpoint, APIAccessLog
from .serializers import (
    APICategorySerializer, APIEndpointSerializer,
    ProxyRequestSerializer, APIAccessLogSerializer
)
from apps.users.models import APIKey, UsageLog
from apps.utils.response import APIResponse


class APICategoryViewSet(viewsets.ModelViewSet):
    """API分类"""
    queryset = APICategory.objects.filter(is_active=True)
    serializer_class = APICategorySerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminUser()]
    
    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(serializer.data, '获取成功')
    
    def retrieve(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return APIResponse.success(serializer.data, '获取成功')
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return APIResponse.created(serializer.data, '创建成功')
    
    def update(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return APIResponse.success(serializer.data, '更新成功')
    
    def destroy(self, request, pk=None):
        instance = self.get_object()
        instance.delete()
        return APIResponse.success(None, '删除成功')


class APIEndpointViewSet(viewsets.ModelViewSet):
    """API端点管理"""
    queryset = APIEndpoint.objects.all()
    serializer_class = APIEndpointSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminUser()]
    
    def get_queryset(self):
        queryset = APIEndpoint.objects.select_related('category').all()
        
        # 分类过滤
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # 搜索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(path__icontains=search) |
                models.Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def list(self, request):
        """获取API列表"""
        queryset = self.get_queryset()
        serializer = APIEndpointSerializer(queryset, many=True)
        return APIResponse.success(serializer.data, '获取成功')
    
    def retrieve(self, request, pk=None):
        """获取单个API"""
        instance = self.get_object()
        serializer = APIEndpointSerializer(instance)
        return APIResponse.success(serializer.data, '获取成功')
    
    def create(self, request):
        """创建API端点"""
        data = request.data
        
        # 处理category字段
        category_id = data.get('category')
        if category_id:
            if isinstance(category_id, int):
                category = APICategory.objects.filter(id=category_id).first()
            elif isinstance(category_id, str) and category_id.isdigit():
                category = APICategory.objects.filter(id=int(category_id)).first()
            else:
                category, _ = APICategory.objects.get_or_create(
                    name=category_id or '默认',
                    defaults={'description': '默认分类'}
                )
        else:
            category, _ = APICategory.objects.get_or_create(
                name='默认',
                defaults={'description': '默认分类'}
            )
        
        endpoint = APIEndpoint.objects.create(
            category=category,
            name=data.get('name', ''),
            path=data.get('path', ''),
            method=data.get('method', 'POST'),
            description=data.get('description', ''),
            target_url=data.get('target_url', ''),
            rate_limit=data.get('rate_limit', 60),
            timeout=data.get('timeout', 30),
            price=data.get('price', 0),
            is_public=data.get('is_public', True),
            is_active=data.get('is_active', True),
        )
        
        serializer = APIEndpointSerializer(endpoint)
        return APIResponse.created(serializer.data, '创建成功')
    
    def update(self, request, pk=None):
        """更新API端点"""
        endpoint = self.get_object()
        data = request.data
        
        # 处理category字段
        category_id = data.get('category')
        if category_id:
            if isinstance(category_id, int):
                endpoint.category_id = category_id
            elif isinstance(category_id, str) and category_id.isdigit():
                endpoint.category_id = int(category_id)
        
        endpoint.name = data.get('name', endpoint.name)
        endpoint.path = data.get('path', endpoint.path)
        endpoint.method = data.get('method', endpoint.method)
        endpoint.description = data.get('description', endpoint.description)
        endpoint.target_url = data.get('target_url', endpoint.target_url)
        endpoint.rate_limit = data.get('rate_limit', endpoint.rate_limit)
        endpoint.timeout = data.get('timeout', endpoint.timeout)
        endpoint.price = data.get('price', endpoint.price)
        endpoint.is_public = data.get('is_public', endpoint.is_public)
        endpoint.is_active = data.get('is_active', endpoint.is_active)
        endpoint.save()
        
        serializer = APIEndpointSerializer(endpoint)
        return APIResponse.success(serializer.data, '更新成功')
    
    def partial_update(self, request, pk=None):
        """部分更新"""
        return self.update(request, pk)
    
    def destroy(self, request, pk=None):
        """删除API端点"""
        instance = self.get_object()
        instance.delete()
        return APIResponse.success(None, '删除成功')
    
    @action(detail=True, methods=['post'])
    def toggle_public(self, request, pk=None):
        """切换公开状态"""
        endpoint = self.get_object()
        endpoint.is_public = not endpoint.is_public
        endpoint.save()
        
        return APIResponse.success({'is_public': endpoint.is_public}, '操作成功')
    
    @action(detail=True, methods=['post'])
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
                return APIResponse.error('需要API Key', 401)
            
            api_key_str = auth_header.split(' ')[1]
            try:
                api_key = APIKey.objects.get(key=api_key_str, is_active=True)
                if api_key.is_expired:
                    return APIResponse.error('API Key已过期', 401)
                user = api_key.user
            except APIKey.DoesNotExist:
                return APIResponse.error('无效的API Key', 401)
        
        # 速率限制检查
        cache_key = f"rate_limit:{api_key.key if api_key else request.META.get('REMOTE_ADDR')}:{endpoint.id}"
        current = cache.get(cache_key, 0)
        limit = api_key.rate_limit if api_key else endpoint.rate_limit
        if current >= limit:
            return APIResponse.error('请求过于频繁', 429)
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
            
            return APIResponse.success({
                'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                'status': response.status_code,
                'response_time': response_time,
            }, '请求成功')
            
        except httpx.TimeoutException:
            log.error_message = '请求超时'
            log.status_code = 504
            log.save()
            return APIResponse.error('请求超时', 504)
        except Exception as e:
            log.error_message = str(e)
            log.status_code = 500
            log.save()
            return APIResponse.error(str(e), 500)


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
