"""
OpenAI兼容格式的API代理视图
支持标准的OpenAI API格式：/v1/chat/completions, /v1/completions, /v1/embeddings等
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
import httpx
import time

from django.core.cache import cache
from apps.users.models import APIKey, UsageLog
from apps.api_proxy.models import APIEndpoint


def get_api_key_from_request(request):
    """从请求中提取API Key"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None, None
    
    api_key_str = auth_header.split(' ')[1]
    try:
        api_key = APIKey.objects.select_related('user').get(key=api_key_str, is_active=True)
        if api_key.is_expired:
            return None, None
        return api_key, api_key.user
    except APIKey.DoesNotExist:
        return None, None


class OpenAIProxyView(APIView):
    """
    OpenAI兼容格式的通用代理
    支持: /v1/chat/completions, /v1/completions, /v1/embeddings
    """
    permission_classes = [AllowAny]
    
    def post(self, request, path=''):
        """处理OpenAI格式的POST请求"""
        return self._handle_request(request, path, 'POST')
    
    def get(self, request, path=''):
        """处理OpenAI格式的GET请求（如模型列表）"""
        return self._handle_request(request, path, 'GET')
    
    def _handle_request(self, request, path, method):
        full_path = f'/v1/{path.strip("/")}'
        
        # 查找对应的API端点
        endpoint = self._find_endpoint(full_path)
        if not endpoint:
            return Response({
                'error': {
                    'message': f'Endpoint {full_path} not found',
                    'type': 'invalid_request_error',
                    'code': 'endpoint_not_found'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 验证API Key
        api_key, user = get_api_key_from_request(request)
        if not endpoint.is_public and not api_key:
            return Response({
                'error': {
                    'message': 'Missing API key',
                    'type': 'authentication_error',
                    'code': 'missing_api_key'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # 速率限制检查
        rate_result = self._check_rate_limit(api_key, endpoint, request)
        if rate_result:
            return rate_result
        
        # 记录使用日志
        start_time = time.time()
        log = UsageLog.objects.create(
            user=user,
            api_key=api_key,
            method=method,
            endpoint=endpoint.path,
        )
        
        # 构建转发请求
        response = self._forward_request(request, endpoint, method)
        response_time = int((time.time() - start_time) * 1000)
        
        # 更新日志
        log.response_time = response_time
        if hasattr(response, 'status_code'):
            log.status_code = response.status_code
            if hasattr(response, 'data'):
                log.response_body = str(response.data)[:5000]
        log.save()
        
        return response
    
    def _find_endpoint(self, path):
        """根据路径查找API端点"""
        path = path.rstrip('/')
        
        # 精确匹配
        endpoint = APIEndpoint.objects.filter(
            path=path, is_active=True
        ).first()
        
        if endpoint:
            return endpoint
        
        # 模糊匹配
        for endpoint in APIEndpoint.objects.filter(is_active=True):
            if path.startswith(endpoint.path.rstrip('/')):
                return endpoint
        
        return None
    
    def _check_rate_limit(self, api_key, endpoint, request):
        """检查速率限制"""
        limit = api_key.rate_limit if api_key else (endpoint.rate_limit or 60)
        cache_key = f"rate_limit:{api_key.key if api_key else 'anonymous'}:{endpoint.id}"
        
        current = cache.get(cache_key, 0)
        if current >= limit:
            return Response({
                'error': {
                    'message': 'Rate limit exceeded',
                    'type': 'rate_limit_error',
                    'code': 'rate_limit_exceeded'
                }
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        cache.set(cache_key, current + 1, 60)
        return None
    
    def _forward_request(self, request, endpoint, method):
        """转发请求到上游API"""
        headers = dict(request.headers)
        headers.pop('Authorization', None)
        
        # 构建URL
        target_url = endpoint.target_url
        if not target_url.endswith('/'):
            target_url += '/'
        
        # 获取请求数据
        data = request.data if method == 'POST' else None
        params = dict(request.query_params)
        
        try:
            with httpx.Client(timeout=endpoint.timeout or 120) as client:
                response = client.request(
                    method=method,
                    url=target_url,
                    headers=headers,
                    params=params,
                    json=data,
                )
                
                try:
                    response_data = response.json()
                except:
                    response_data = {'raw': response.text}
                
                return Response(response_data, status=response.status_code)
                
        except httpx.TimeoutException:
            return Response({
                'error': {
                    'message': 'Request timeout',
                    'type': 'timeout_error',
                    'code': 'request_timeout'
                }
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except Exception as e:
            return Response({
                'error': {
                    'message': str(e),
                    'type': 'server_error',
                    'code': 'upstream_error'
                }
            }, status=status.HTTP_502_BAD_GATEWAY)


@api_view(['GET'])
@permission_classes([AllowAny])
def models_list(request):
    """
    返回可用的模型列表（OpenAI格式）
    GET /v1/models
    """
    from apps.ai_models.models import AIModel
    
    models = AIModel.objects.filter(is_active=True).values(
        'id', 'name', 'provider__name', 'description'
    )
    
    # 转换为OpenAI格式
    data = {
        'object': 'list',
        'data': [
            {
                'id': f"{m['provider__name'].lower()}-{m['name'].lower().replace(' ', '-')}" if m['provider__name'] else m['name'].lower().replace(' ', '-'),
                'object': 'model',
                'created': 1677610602,
                'owned_by': m['provider__name'] or 'unknown',
                'permission': [],
                'root': m['name'],
                'parent': None,
            }
            for m in models
        ]
    }
    
    return Response(data)


class StreamProxyView(APIView):
    """
    流式响应代理（用于chat completions streaming）
    """
    permission_classes = [AllowAny]
    
    def post(self, request, path=''):
        full_path = f'/v1/{path.strip("/")}'
        
        # 查找端点
        endpoint = None
        for ep in APIEndpoint.objects.filter(is_active=True):
            if full_path.startswith(ep.path.rstrip('/')):
                endpoint = ep
                break
        
        if not endpoint:
            return Response({'error': 'Endpoint not found'}, status=404)
        
        # 验证API Key
        api_key, user = get_api_key_from_request(request)
        if not endpoint.is_public and not api_key:
            return Response({'error': 'Missing API key'}, status=401)
        
        # 转发流式请求
        return self._forward_stream(request, endpoint, api_key, user)
    
    def _forward_stream(self, request, endpoint, api_key, user):
        """转发流式请求"""
        headers = dict(request.headers)
        headers.pop('Authorization', None)
        
        target_url = endpoint.target_url
        if not target_url.endswith('/'):
            target_url += '/'
        
        try:
            with httpx.Client(timeout=endpoint.timeout or 300, stream=True) as client:
                response = client.post(
                    target_url,
                    headers=headers,
                    json=request.data,
                )
                
                # 流式返回
                def generate():
                    for chunk in response.iter_bytes():
                        if chunk:
                            yield chunk
                
                from django.http import StreamingHttpResponse
                return StreamingHttpResponse(
                    generate(),
                    content_type='text/event-stream'
                )
        except Exception as e:
            return Response({'error': str(e)}, status=502)
