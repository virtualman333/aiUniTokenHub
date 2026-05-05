"""
OpenAI兼容格式的API代理视图
支持标准的OpenAI API格式：/v1/chat/completions, /v1/completions, /v1/embeddings, /v1/models
"""
from __future__ import annotations

import json
import time
from typing import Optional

import httpx
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.http import StreamingHttpResponse
from django.core.cache import cache

from apps.users.models import APIKey, UsageLog
from apps.ai_models.models import AIModel
from .models import APIAccessLog
from .models_channel import APIChannel, ModelChannelBinding


# ============== 工具函数 ==============

def get_api_key_from_request(request) -> tuple:
    """从请求中提取API Key，返回 (api_key, user) 或 (None, None)"""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header:
        return None, None
    
    if auth_header.startswith('Bearer '):
        api_key_str = auth_header.split(' ')[1]
    elif auth_header.startswith('sk-'):
        api_key_str = auth_header
    else:
        return None, None
    
    try:
        api_key = APIKey.objects.select_related('user').get(key=api_key_str, is_active=True)
        if api_key.is_expired:
            return None, None
        return api_key, api_key.user
    except APIKey.DoesNotExist:
        return None, None


def select_channel_for_model(model_code: str) -> Optional[APIChannel]:
    """
    根据模型代码选择最优渠道（加权负载均衡 + 故障转移）
    """
    try:
        model = AIModel.objects.get(code=model_code, status='active')
    except AIModel.DoesNotExist:
        return None
    
    # 获取模型关联的渠道
    bindings = ModelChannelBinding.objects.filter(
        model=model,
        is_active=True
    ).select_related('channel').order_by('priority')
    
    # 收集可用渠道及其权重
    available_channels = []
    for binding in bindings:
        channel = binding.channel
        if channel.status == 'active':
            # 检查渠道是否有可用额度
            if channel.remaining_quota is None or channel.remaining_quota > 0:
                available_channels.append((channel, binding.priority))
    
    if not available_channels:
        # 如果没有绑定渠道，尝试获取默认渠道
        default_channels = APIChannel.objects.filter(
            status='active',
            is_default=True
        )
        for ch in default_channels:
            if ch.remaining_quota is None or ch.remaining_quota > 0:
                available_channels.append((ch, 100))
    
    if not available_channels:
        # 尝试任意可用渠道
        all_channels = APIChannel.objects.filter(status='active')
        for ch in all_channels:
            if ch.remaining_quota is None or ch.remaining_quota > 0:
                available_channels.append((ch, 50))
    
    if not available_channels:
        return None
    
    # 加权随机选择（权重 = priority * base_weight）
    # priority 越高，被选中的概率越大
    total_weight = sum(weight for _, weight in available_channels)
    if total_weight == 0:
        return available_channels[0][0] if available_channels else None
    
    import random
    rand_val = random.randint(1, total_weight)
    cumulative = 0
    for channel, weight in available_channels:
        cumulative += weight
        if rand_val <= cumulative:
            return channel
    
    return available_channels[0][0]


def check_rate_limit(api_key: APIKey, channel: APIChannel) -> Optional[Response]:
    """检查速率限制"""
    limit = min(api_key.rate_limit, channel.max_qps)
    cache_key = f"rate_limit:{api_key.key}:{channel.id}"
    
    current = cache.get(cache_key, 0)
    if current >= limit:
        return Response({
            'error': {
                'message': 'Rate limit exceeded. Please retry later.',
                'type': 'rate_limit_error',
                'param': None,
                'code': 'rate_limit_exceeded'
            }
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    cache.set(cache_key, current + 1, 60)
    return None


def log_api_access(api_key, user, method, path, request_body, response_data, 
                   response_status, response_time, ip_address=''):
    """记录API访问日志"""
    try:
        APIAccessLog.objects.create(
            api_key=api_key,
            user=user,
            method=method,
            path=path,
            request_body=json.dumps(request_body)[:10000] if request_body else '',
            response_body=json.dumps(response_data)[:5000] if isinstance(response_data, dict) else str(response_data)[:5000],
            response_status=response_status,
            response_time=response_time,
            ip_address=ip_address,
        )
    except Exception:
        pass


def get_client_ip(request) -> str:
    """获取客户端IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


# ============== OpenAI 兼容接口 ==============

class ChatCompletionsView(APIView):
    """
    OpenAI Chat Completions API
    POST /v1/chat/completions
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        return self._handle_chat_completions(request)
    
    def get(self, request):
        """支持GET请求获取URL（调试用）"""
        return Response({
            'error': {
                'message': 'This endpoint only supports POST requests.',
                'type': 'invalid_request_error',
                'param': None,
                'code': 'invalid_request'
            }
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def _handle_chat_completions(self, request):
        """处理聊天补全请求"""
        start_time = time.time()
        
        # 获取模型名称
        model_name = request.data.get('model')
        if not model_name:
            return Response({
                'error': {
                    'message': 'Missing required parameter: model',
                    'type': 'invalid_request_error',
                    'param': 'model',
                    'code': 'missing_required_parameter'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证API Key
        api_key, user = get_api_key_from_request(request)
        if not api_key:
            return Response({
                'error': {
                    'message': 'Incorrect API key provided.',
                    'type': 'authentication_error',
                    'param': None,
                    'code': 'invalid_api_key'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # 检查用户状态
        if not user.is_active:
            return Response({
                'error': {
                    'message': 'User account is disabled.',
                    'type': 'authentication_error',
                    'code': 'user_disabled'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # 检查API Key额度
        if api_key.remaining_calls is not None and api_key.remaining_calls <= 0:
            return Response({
                'error': {
                    'message': 'API key quota exceeded.',
                    'type': 'rate_limit_error',
                    'code': 'quota_exceeded'
                }
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # 选择渠道
        channel = select_channel_for_model(model_name)
        if not channel:
            return Response({
                'error': {
                    'message': f'Model {model_name} is not available.',
                    'type': 'invalid_request_error',
                    'param': 'model',
                    'code': 'model_not_found'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 检查速率限制
        rate_limit_error = check_rate_limit(api_key, channel)
        if rate_limit_error:
            return rate_limit_error
        
        # 判断是否流式响应
        is_streaming = request.data.get('stream', False)
        
        if is_streaming:
            return self._handle_streaming(request, api_key, user, channel, model_name, start_time)
        else:
            return self._handle_normal(request, api_key, user, channel, model_name, start_time)
    
    def _handle_normal(self, request, api_key, user, channel, model_name, start_time):
        """处理普通（非流式）请求"""
        # 构建转发请求
        headers = self._build_headers(request)
        headers['Authorization'] = f'Bearer {channel.api_key}'
        
        url = channel.base_url.rstrip('/')
        
        # 记录使用日志
        usage_log = UsageLog.objects.create(
            user=user,
            api_key=api_key,
            method='POST',
            endpoint='/v1/chat/completions',
        )
        
        try:
            timeout = channel.timeout or 120
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    url,
                    headers=headers,
                    json=request.data,
                    timeout=timeout,
                )
            
            response_time = int((time.time() - start_time) * 1000)
            
            # 解析响应
            try:
                response_data = response.json()
            except:
                response_data = {'raw_response': response.text}
            
            # 更新日志
            self._update_usage_log(usage_log, response, response_data, response_time)
            
            # 更新渠道统计
            channel.increment_calls(success=response.status_code < 400, latency=response_time)
            
            # 记录访问日志
            log_api_access(
                api_key, user, 'POST', '/v1/chat/completions',
                request.data, response_data, response.status_code,
                response_time, get_client_ip(request)
            )
            
            return Response(response_data, status=response.status_code)
            
        except httpx.TimeoutException:
            channel.increment_calls(success=False, latency=int((time.time() - start_time) * 1000))
            return Response({
                'error': {
                    'message': 'Request timeout. Please try again.',
                    'type': 'timeout_error',
                    'code': 'request_timeout'
                }
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
            
        except Exception as e:
            channel.increment_calls(success=False, latency=int((time.time() - start_time) * 1000))
            return Response({
                'error': {
                    'message': f'Internal server error: {str(e)}',
                    'type': 'server_error',
                    'code': 'internal_error'
                }
            }, status=status.HTTP_502_BAD_GATEWAY)
    
    def _handle_streaming(self, request, api_key, user, channel, model_name, start_time):
        """处理流式请求"""
        headers = self._build_headers(request)
        headers['Authorization'] = f'Bearer {channel.api_key}'
        
        url = channel.base_url.rstrip('/')
        
        # 记录使用日志
        usage_log = UsageLog.objects.create(
            user=user,
            api_key=api_key,
            method='POST',
            endpoint='/v1/chat/completions',
        )
        
        try:
            timeout = channel.timeout or 300
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    url,
                    headers=headers,
                    json=request.data,
                    stream=True,
                )
            
            response_time = 0
            
            def generate():
                """生成器函数，流式返回SSE数据"""
                for chunk in response.iter_bytes():
                    if chunk:
                        # 保持原始SSE格式
                        yield chunk
                
                # 标记完成
                channel.increment_calls(success=True, latency=int((time.time() - start_time) * 1000))
            
            streaming_response = StreamingHttpResponse(
                generate(),
                content_type='text/event-stream'
            )
            streaming_response['Cache-Control'] = 'no-cache'
            streaming_response['Connection'] = 'keep-alive'
            streaming_response['X-Request-ID'] = str(usage_log.id)
            
            return streaming_response
            
        except httpx.TimeoutException:
            channel.increment_calls(success=False, latency=int((time.time() - start_time) * 1000))
            return Response({
                'error': {
                    'message': 'Request timeout.',
                    'type': 'timeout_error',
                    'code': 'request_timeout'
                }
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
            
        except Exception as e:
            channel.increment_calls(success=False, latency=int((time.time() - start_time) * 1000))
            return Response({
                'error': {
                    'message': f'Internal server error: {str(e)}',
                    'type': 'server_error',
                    'code': 'internal_error'
                }
            }, status=status.HTTP_502_BAD_GATEWAY)
    
    def _build_headers(self, request) -> dict:
        """构建转发请求头"""
        headers = {}
        skip_keys = ['host', 'content-length', 'authorization']
        for key, value in request.headers.items():
            if key.lower() not in skip_keys:
                headers[key] = value
        return headers
    
    def _update_usage_log(self, log, response, response_data, response_time):
        """更新使用日志"""
        log.response_time = response_time
        log.status_code = response.status_code
        
        # 计算token使用量（如果有）
        if isinstance(response_data, dict):
            usage = response_data.get('usage', {})
            log.input_tokens = usage.get('prompt_tokens', 0)
            log.output_tokens = usage.get('completion_tokens', 0)
            log.total_tokens = usage.get('total_tokens', 0)
            
            if hasattr(response, 'headers'):
                log.response_body = str(response_data)[:5000]
        
        log.save()


class CompletionsView(APIView):
    """
    OpenAI Completions API (Legacy)
    POST /v1/completions
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # 验证API Key
        api_key, user = get_api_key_from_request(request)
        if not api_key:
            return Response({
                'error': {
                    'message': 'Incorrect API key provided.',
                    'type': 'authentication_error',
                    'code': 'invalid_api_key'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        model_name = request.data.get('model')
        if not model_name:
            return Response({
                'error': {
                    'message': 'Missing required parameter: model',
                    'type': 'invalid_request_error',
                    'param': 'model'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 选择渠道
        channel = select_channel_for_model(model_name)
        if not channel:
            return Response({
                'error': {
                    'message': f'Model {model_name} is not available.',
                    'type': 'invalid_request_error',
                    'code': 'model_not_found'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 转发请求
        headers = {
            'Authorization': f'Bearer {channel.api_key}',
            'Content-Type': 'application/json',
        }
        
        base_url = channel.base_url.rstrip('/')
        url = f"{base_url}/v1/completions"
        
        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(url, headers=headers, json=request.data)
            
            return Response(response.json(), status=response.status_code)
        except Exception as e:
            return Response({
                'error': {
                    'message': str(e),
                    'type': 'server_error',
                    'code': 'upstream_error'
                }
            }, status=status.HTTP_502_BAD_GATEWAY)


class EmbeddingsView(APIView):
    """
    OpenAI Embeddings API
    POST /v1/embeddings
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # 验证API Key
        api_key, user = get_api_key_from_request(request)
        if not api_key:
            return Response({
                'error': {
                    'message': 'Incorrect API key provided.',
                    'type': 'authentication_error',
                    'code': 'invalid_api_key'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        model_name = request.data.get('model', 'text-embedding-ada-002')
        
        # 选择渠道
        channel = select_channel_for_model(model_name)
        if not channel:
            # 尝试通用embeddings渠道
            channel = APIChannel.objects.filter(status='active', is_default=True).first()
            if not channel:
                return Response({
                    'error': {
                        'message': 'No embedding service available.',
                        'code': 'model_not_found'
                    }
                }, status=status.HTTP_404_NOT_FOUND)
        
        headers = {
            'Authorization': f'Bearer {channel.api_key}',
            'Content-Type': 'application/json',
        }
        
        base_url = channel.base_url.rstrip('/')
        url = f"{base_url}/v1/embeddings"
        
        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(url, headers=headers, json=request.data)
            
            return Response(response.json(), status=response.status_code)
        except Exception as e:
            return Response({
                'error': {
                    'message': str(e),
                    'type': 'server_error',
                    'code': 'upstream_error'
                }
            }, status=status.HTTP_502_BAD_GATEWAY)


@api_view(['GET'])
@permission_classes([AllowAny])  # noqa
def models_list(request):
    """
    返回可用的模型列表（OpenAI格式）
    GET /v1/models
    """
    models = AIModel.objects.filter(status='active').select_related('provider')
    
    data = {
        'object': 'list',
        'data': [
            {
                'id': m.code,
                'object': 'model',
                'created': int(m.created_at.timestamp()) if m.created_at else 1677610602,
                'owned_by': m.provider.name if m.provider else 'unknown',
                'permission': [{
                    'id': f'modelperm-{m.code}',
                    'object': 'model_permission',
                    'created': int(m.created_at.timestamp()) if m.created_at else 1677610602,
                    'allow_create_engine': True,
                    'allow_sampling': True,
                    'allow_logprobs': True,
                    'allow_view': True,
                    'allow_fine_tuning': False,
                    'deny': [],
                }],
                'root': m.code,
                'parent': None,
            }
            for m in models
        ]
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def model_retrieve(request, model_id):
    """
    获取特定模型信息（OpenAI格式）
    GET /v1/models/{model_id}
    """
    try:
        model = AIModel.objects.select_related('provider').get(code=model_id, status='active')
        
        data = {
            'id': model.code,
            'object': 'model',
            'created': int(model.created_at.timestamp()) if model.created_at else 1677610602,
            'owned_by': model.provider.name if model.provider else 'unknown',
            'permission': [{
                'id': f'modelperm-{model.code}',
                'object': 'model_permission',
                'created': int(model.created_at.timestamp()) if model.created_at else 1677610602,
                'allow_create_engine': True,
                'allow_sampling': True,
                'allow_logprobs': True,
                'allow_view': True,
                'allow_fine_tuning': False,
                'deny': [],
            }],
            'root': model.code,
            'parent': None,
        }
        
        return Response(data)
    except AIModel.DoesNotExist:
        return Response({
            'error': {
                'message': f'Model {model_id} not found',
                'type': 'invalid_request_error',
                'param': 'model_id',
                'code': 'model_not_found'
            }
        }, status=status.HTTP_404_NOT_FOUND)


class ModelsView(APIView):
    """
    通用模型视图 - 处理所有 /v1/* 请求
    """
    permission_classes = [AllowAny]
    
    def get(self, request, path=''):
        """处理GET请求"""
        if path == 'models':
            return models_list(request)
        elif path.startswith('models/'):
            model_id = path.replace('models/', '')
            return model_retrieve(request, model_id)
        else:
            return Response({
                'error': {
                    'message': f'Endpoint not found: /v1/{path}',
                    'type': 'invalid_request_error',
                    'code': 'not_found'
                }
            }, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request, path=''):
        """处理POST请求"""
        if path == 'chat/completions':
            chat_view = ChatCompletionsView()
            return chat_view.post(request)
        elif path == 'completions':
            completions_view = CompletionsView()
            return completions_view.post(request)
        elif path == 'embeddings':
            embeddings_view = EmbeddingsView()
            return embeddings_view.post(request)
        else:
            return Response({
                'error': {
                    'message': f'Endpoint not found: /v1/{path}',
                    'type': 'invalid_request_error',
                    'code': 'not_found'
                }
            }, status=status.HTTP_404_NOT_FOUND)
