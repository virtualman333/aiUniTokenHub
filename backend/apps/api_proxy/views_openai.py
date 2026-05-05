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
from apps.ai_models.models import AIModel
from apps.ai_models.upstream_models import UpstreamAccount, ModelUpstreamAccount


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


def select_upstream_account(model_code):
    """
    根据模型代码选择上游账号（加权负载均衡）
    """
    # 查找模型
    try:
        model = AIModel.objects.get(code=model_code, status='active')
    except AIModel.DoesNotExist:
        return None
    
    # 获取模型关联的账号
    bindings = ModelUpstreamAccount.objects.filter(
        model=model,
        is_enabled=True
    ).select_related('account')
    
    if not bindings.exists():
        return None
    
    # 加权随机选择
    import random
    total_weight = sum(b.weight for b in bindings)
    rand = random.uniform(0, total_weight)
    
    cumulative = 0
    for binding in bindings:
        cumulative += binding.weight
        if rand <= cumulative:
            return binding.account
    
    return bindings.first().account


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
        # 获取模型名称
        model_name = None
        if path in ['chat/completions', 'completions', 'embeddings']:
            model_name = request.data.get('model')
        
        if not model_name:
            return Response({
                'error': {
                    'message': f'Missing model parameter',
                    'type': 'invalid_request_error',
                    'code': 'missing_model'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 选择上游账号
        account = select_upstream_account(model_name)
        if not account:
            return Response({
                'error': {
                    'message': f'No available upstream account for model {model_name}',
                    'type': 'server_error',
                    'code': 'no_upstream'
                }
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # 验证API Key
        api_key, user = get_api_key_from_request(request)
        if not api_key:
            return Response({
                'error': {
                    'message': 'Missing API key',
                    'type': 'authentication_error',
                    'code': 'missing_api_key'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # 速率限制检查
        rate_result = self._check_rate_limit(api_key, account)
        if rate_result:
            return rate_result
        
        # 记录使用日志
        start_time = time.time()
        log = UsageLog.objects.create(
            user=user,
            api_key=api_key,
            method=method,
            endpoint=f'/v1/{path}',
        )
        
        # 构建转发请求
        response = self._forward_request(request, account, method)
        response_time = int((time.time() - start_time) * 1000)
        
        # 更新日志
        log.response_time = response_time
        if hasattr(response, 'status_code'):
            log.status_code = response.status_code
            if hasattr(response, 'data'):
                log.response_body = str(response.data)[:5000]
        log.save()
        
        # 更新账号使用统计
        account.usage_count += 1
        account.save()
        
        return response
    
    def _check_rate_limit(self, api_key, account):
        """检查速率限制"""
        limit = min(api_key.rate_limit, account.max_rpm)
        cache_key = f"rate_limit:{api_key.key}:{account.id}"
        
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
    
    def _forward_request(self, request, account, method):
        """转发请求到上游API"""
        headers = dict(request.headers)
        headers.pop('Authorization', None)
        
        # 构建URL
        base_url = account.base_url.rstrip('/')
        
        # 获取请求数据
        data = request.data if method == 'POST' else None
        params = dict(request.query_params)
        
        try:
            timeout = account.timeout or 120
            with httpx.Client(timeout=timeout) as client:
                # 如果账号有API密钥，设置Authorization头
                if account.api_key:
                    headers['Authorization'] = f'Bearer {account.api_key}'
                
                response = client.request(
                    method=method,
                    url=f"{base_url}/v1/chat/completions",
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
    models = AIModel.objects.filter(status='active').select_related('provider').values(
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
        model_name = request.data.get('model')
        
        if not model_name:
            return Response({'error': 'Missing model parameter'}, status=400)
        
        # 选择上游账号
        account = select_upstream_account(model_name)
        if not account:
            return Response({'error': f'No available upstream account for model {model_name}'}, status=503)
        
        # 验证API Key
        api_key, user = get_api_key_from_request(request)
        if not api_key:
            return Response({'error': 'Missing API key'}, status=401)
        
        # 转发流式请求
        return self._forward_stream(request, account, api_key, user)
    
    def _forward_stream(self, request, account, api_key, user):
        """转发流式请求"""
        headers = dict(request.headers)
        headers.pop('Authorization', None)
        
        base_url = account.base_url.rstrip('/')
        
        # 如果账号有API密钥，设置Authorization头
        if account.api_key:
            headers['Authorization'] = f'Bearer {account.api_key}'
        
        try:
            with httpx.Client(timeout=account.timeout or 300, stream=True) as client:
                response = client.post(
                    f"{base_url}/v1/chat/completions",
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
