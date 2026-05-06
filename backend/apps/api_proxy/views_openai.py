"""
OpenAI兼容格式的API代理视图
支持标准的OpenAI API格式：/v1/chat/completions, /v1/completions, /v1/embeddings, /v1/models
"""
from __future__ import annotations

import json
import time
import logging
from decimal import Decimal
from typing import Optional

import httpx
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from django.http import StreamingHttpResponse
from django.core.cache import cache

from apps.users.models import APIKey, UsageLog, Bill
from apps.ai_models.models import AIModel
from apps.ai_models.upstream_models import UpstreamAccount, ModelUpstreamAccount
from .models import APIAccessLog


logger = logging.getLogger('api_proxy')


class EventStreamRenderer(BaseRenderer):
    """
    用于 SSE 流式响应的 Renderer。
    仅声明媒体类型，让 DRF 的内容协商通过 ``Accept: text/event-stream``。
    实际响应由视图直接返回 ``StreamingHttpResponse``，不会调用 render()。
    """

    media_type = 'text/event-stream'
    format = 'event-stream'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b''
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        if isinstance(data, str):
            return data.encode(self.charset)
        return json.dumps(data, ensure_ascii=False).encode(self.charset)



# ============== 工具函数 ==============

def build_endpoint_url(base_url: str, endpoint: str = 'chat/completions') -> str:
    """
    构建完整的 API 端点 URL
    base_url 应该包含完整的路径前缀（如 /v1），直接拼接 endpoint
    """
    base = base_url.rstrip('/')
    return f"{base}/{endpoint}"

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


def select_upstream_account(model_code: str) -> Optional[UpstreamAccount]:
    """
    根据模型代码选择最优上游账号（加权负载均衡 + 故障转移）
    """
    logger.info(f"[select_account] Looking for model: {model_code}")
    
    try:
        # 查找模型
        model = AIModel.objects.filter(code=model_code, status='active').first()
        if not model:
            # 尝试通过 api_model_id 查找
            model = AIModel.objects.filter(api_model_id=model_code, status='active').first()
        
        if not model:
            logger.warning(f"[select_account] Model not found: {model_code}")
            return None
            
        logger.info(f"[select_account] Found model: {model.name} (id={model.id})")
    except Exception as e:
        logger.error(f"[select_account] Error finding model: {e}")
        return None
    
    # 获取模型关联的上游账号
    bindings = ModelUpstreamAccount.objects.filter(
        model=model,
        is_enabled=True
    ).select_related('account').order_by('-weight')
    
    logger.info(f"[select_account] Found {bindings.count()} upstream account bindings for model")
    
    # 收集可用账号及其权重
    available_accounts = []
    for binding in bindings:
        account = binding.account
        logger.info(f"[select_account] Checking account: {account.name}, is_active={account.is_active}, is_available={account.is_available}")
        if account.is_active and account.is_available:
            available_accounts.append((account, binding.weight))
            logger.info(f"[select_account] Account {account.name} is available (weight={binding.weight})")
    
    if not available_accounts:
        logger.warning(f"[select_account] No available bindings for model")
        return None
    
    # 加权随机选择（权重越高被选中的概率越大）
    total_weight = sum(weight for _, weight in available_accounts)
    if total_weight == 0:
        selected = available_accounts[0][0]
    else:
        import random
        rand_val = random.randint(1, total_weight)
        cumulative = 0
        for account, weight in available_accounts:
            cumulative += weight
            if cumulative >= rand_val:
                selected = account
                break
        else:
            selected = available_accounts[0][0]
    
    logger.info(f"[select_account] Selected account: {selected.name}, base_url: {selected.base_url}, api_key: {'***' + selected.api_key[-8:] if selected.api_key else 'None'}")
    return selected


def check_rate_limit(api_key: APIKey, account: UpstreamAccount) -> Optional[Response]:
    """检查速率限制"""
    limit = min(api_key.rate_limit, account.max_rpm)
    cache_key = f"rate_limit:{api_key.key}:{account.id}"
    
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


def update_upstream_usage(account: UpstreamAccount, success: bool = True):
    """更新上游账号使用统计"""
    try:
        # 先检查 UpstreamAccount 是否有统计字段
        # （这些字段实际定义在 ModelUpstreamAccount 上，UpstreamAccount 可能没有）
        if not hasattr(account, 'usage_count'):
            return
        account.usage_count += 1
        if not success:
            account.error_count += 1
        from django.utils import timezone
        account.last_used = timezone.now()
        account.save(update_fields=['usage_count', 'error_count', 'last_used'])
    except Exception as e:
        logger.error(f"[update_upstream_usage] Error updating usage: {e}")


def log_api_access(api_key, user, method, path, request_body, response_data,
                   response_status, response_time, ip_address='', model=None, upstream_account=None,
                   input_tokens=0, output_tokens=0, total_tokens=0, cached_tokens=0, cost=0):
    """记录API访问日志"""
    try:
        APIAccessLog.objects.create(
            api_key=api_key,
            user=user,
            method=method,
            path=path,
            model=model,
            upstream_account=upstream_account,
            request_body=json.dumps(request_body)[:10000] if request_body else '',
            response_body=json.dumps(response_data)[:5000] if isinstance(response_data, dict) else str(response_data)[:5000],
            response_status=response_status,
            response_time=response_time,
            ip_address=ip_address,
            input_tokens=int(input_tokens or 0),
            output_tokens=int(output_tokens or 0),
            total_tokens=int(total_tokens or 0),
            cached_tokens=int(cached_tokens or 0),
            cost=cost or 0,
        )
    except Exception:
        pass


def get_client_ip(request) -> str:
    """获取客户端IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def calculate_and_deduct_cost(user, model_code, input_tokens, output_tokens,
                              usage_log=None, cached_tokens: int = 0):
    """
    根据 token 用量和模型定价计算费用并扣减用户余额。
    单价单位：元 / 百万 tokens

    - input_tokens: 总的提示 tokens（包含缓存命中部分）
    - cached_tokens: 其中命中缓存的 tokens；按 cached_input_price 计费
    - output_tokens: 输出 tokens
    返回 (cost, success)
    """
    try:
        model = AIModel.objects.filter(code=model_code, status='active').first()
        if not model:
            return 0, False
    except Exception:
        return 0, False

    PER_MILLION = 1_000_000.0

    cached_tokens = max(0, int(cached_tokens or 0))
    input_tokens = max(0, int(input_tokens or 0))
    output_tokens = max(0, int(output_tokens or 0))

    cached_tokens = min(cached_tokens, input_tokens)
    non_cached_input = input_tokens - cached_tokens

    input_price = float(model.input_price or 0)
    output_price = float(model.output_price or 0)
    cached_price = float(model.cached_input_price or 0)
    effective_cached_price = cached_price if cached_price > 0 else input_price

    input_cost = (non_cached_input / PER_MILLION) * input_price
    cached_cost = (cached_tokens / PER_MILLION) * effective_cached_price
    output_cost = (output_tokens / PER_MILLION) * output_price
    cost = round(input_cost + cached_cost + output_cost, 6)

    # 把成本回写到 usage_log（即使不扣款也记录费用）
    if usage_log is not None:
        try:
            usage_log.cost = cost
            usage_log.cached_tokens = cached_tokens
            usage_log.save(update_fields=['cost', 'cached_tokens'])
        except Exception:
            pass

    if cost <= 0:
        return 0, True

    # 余额不足：仍记录费用，但不扣款（业务可调整）
    if user.balance < Decimal(str(cost)):
        return cost, False

    user.balance -= Decimal(str(cost))
    user.save(update_fields=['balance'])

    desc_parts = [f'输入{input_tokens}tokens']
    if cached_tokens > 0:
        desc_parts.append(f'其中缓存{cached_tokens}')
    desc_parts.append(f'输出{output_tokens}tokens')
    description = f'API调用 {model_code} ({", ".join(desc_parts)})'

    Bill.objects.create(
        user=user,
        type='consume',
        amount=-cost,
        balance=user.balance,
        description=description,
        usage_log=usage_log
    )
    return cost, True


# ============== OpenAI 兼容接口 ==============

class ChatCompletionsView(APIView):
    """
    OpenAI Chat Completions API
    POST /v1/chat/completions
    """
    permission_classes = [AllowAny]
    # 同时支持 application/json 与 text/event-stream，避免 SSE 客户端因 Accept 报 406
    renderer_classes = [JSONRenderer, EventStreamRenderer]
    
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
        
        # 选择上游账号
        account = select_upstream_account(model_name)
        if not account:
            return Response({
                'error': {
                    'message': f'Model {model_name} is not available or no upstream account configured.',
                    'type': 'invalid_request_error',
                    'param': 'model',
                    'code': 'model_not_found'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 日志记录路由信息
        logger.info(f"[ChatCompletions] model={model_name}, user={user.id}, account={account.name}")
        logger.info(f"[ChatCompletions] Account base_url: {account.base_url}")
        logger.info(f"[ChatCompletions] Account api_key: {'***' + account.api_key[-8:] if account.api_key else 'None'}")
        
        # 检查速率限制
        rate_limit_error = check_rate_limit(api_key, account)
        if rate_limit_error:
            return rate_limit_error
        
        # 判断是否流式响应
        is_streaming = request.data.get('stream', False)
        
        if is_streaming:
            return self._handle_streaming(request, api_key, user, account, model_name, start_time)
        else:
            return self._handle_normal(request, api_key, user, account, model_name, start_time)
    
    def _handle_normal(self, request, api_key, user, account, model_name, start_time):
        """处理普通（非流式）请求"""
        # 获取 AIModel 对象
        model_obj = AIModel.objects.filter(code=model_name).first()
        
        # 构建转发请求
        headers = self._build_headers(request)
        headers['Authorization'] = f'Bearer {account.api_key}'
        
        # 构建目标 URL
        target_url = build_endpoint_url(account.base_url, 'chat/completions')
        
        # 日志记录转发信息
        logger.info(f"[ChatCompletions-Normal] model={model_name}, user_id={user.id}, account={account.name}")
        logger.info(f"[ChatCompletions-Normal] Account base_url: {account.base_url}")
        logger.info(f"[ChatCompletions-Normal] Forwarding to: {target_url}")
        logger.debug(f"[ChatCompletions-Normal] Request headers: {headers}")
        
        # 记录使用日志
        usage_log = UsageLog.objects.create(
            user=user,
            api_key=api_key,
            method='POST',
            endpoint='/chat/completions',
        )
        
        try:
            timeout = 120  # 默认超时120秒
            logger.info(f"[ChatCompletions-Normal] Sending request, timeout={timeout}s")
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    target_url,
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
            
            # 错误日志记录
            if response.status_code >= 400:
                logger.error(
                    f"[ChatCompletions-Error] user_id={user.id}, account={account.name}, "
                    f"status={response.status_code}, response={response_data}"
                )
            else:
                logger.info(f"[ChatCompletions-Normal] Success, status={response.status_code}")
            
            # 更新日志（含计费）
            self._update_usage_log(usage_log, response, response_data, response_time, model_name)
            usage_log.refresh_from_db()  # 拿到计费后的最新值
            
            # 更新上游账号使用统计
            update_upstream_usage(account, success=response.status_code < 400)
            
            # 记录访问日志（带 token / cost）
            log_api_access(
                api_key, user, 'POST', '/chat/completions',
                request.data, response_data, response.status_code,
                response_time, get_client_ip(request),
                model=model_obj, upstream_account=account,
                input_tokens=usage_log.input_tokens,
                output_tokens=usage_log.output_tokens,
                total_tokens=usage_log.total_tokens,
                cached_tokens=usage_log.cached_tokens,
                cost=usage_log.cost,
            )
            
            # 如果是错误响应，确保返回完整的错误信息
            if response.status_code >= 400:
                if isinstance(response_data, dict) and 'error' not in response_data:
                    response_data = {
                        'error': {
                            'message': response_data.get('message', response_data.get('error', str(response_data))),
                            'type': response_data.get('type', 'upstream_error'),
                            'code': response_data.get('code', f'http_{response.status_code}'),
                            'original_response': response_data
                        }
                    }
                return Response(response_data, status=response.status_code)
            
            return Response(response_data, status=response.status_code)
            
        except httpx.TimeoutException:
            update_upstream_usage(account, success=False)
            response_time = int((time.time() - start_time) * 1000)
            try:
                log_api_access(
                    api_key, user, 'POST', '/chat/completions',
                    request.data, {'error': {'message': 'Request timeout'}}, 504,
                    response_time, get_client_ip(request),
                    model=model_obj, upstream_account=account,
                )
            except Exception:
                pass
            return Response({
                'error': {
                    'message': 'Request timeout. Please try again.',
                    'type': 'timeout_error',
                    'code': 'request_timeout'
                }
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)

        except Exception as e:
            update_upstream_usage(account, success=False)
            response_time = int((time.time() - start_time) * 1000)
            try:
                log_api_access(
                    api_key, user, 'POST', '/chat/completions',
                    request.data, {'error': {'message': str(e)}}, 502,
                    response_time, get_client_ip(request),
                    model=model_obj, upstream_account=account,
                )
            except Exception:
                pass
            return Response({
                'error': {
                    'message': f'Internal server error: {str(e)}',
                    'type': 'server_error',
                    'code': 'internal_error'
                }
            }, status=status.HTTP_502_BAD_GATEWAY)
    
    def _handle_streaming(self, request, api_key, user, account, model_name, start_time):
        """处理流式请求"""
        headers = self._build_headers(request)
        headers['Authorization'] = f'Bearer {account.api_key}'
        # 关键：明确告诉上游用流式
        headers['Accept'] = 'text/event-stream'
        # 移除可能导致缓冲的压缩
        headers.pop('Accept-Encoding', None)
        headers.pop('accept-encoding', None)

        # 构建目标 URL
        target_url = build_endpoint_url(account.base_url, 'chat/completions')

        # 日志记录转发信息
        logger.info(f"[ChatCompletions-Stream] model={model_name}, user_id={user.id}, account={account.name}")
        logger.info(f"[ChatCompletions-Stream] Account base_url: {account.base_url}")
        logger.debug(f"[ChatCompletions-Stream] Request headers: {headers}")

        # 提前抓取请求级别的信息，防止生成器执行时请求已关闭
        client_ip = get_client_ip(request)
        request_data_copy = {k: v for k, v in request.data.items()} if hasattr(request.data, 'items') else dict(request.data or {})
        model_obj = AIModel.objects.filter(code=model_name).first()

        # 记录使用日志
        usage_log = UsageLog.objects.create(
            user=user,
            api_key=api_key,
            method='POST',
            endpoint='/chat/completions',
        )

        try:
            timeout = 300  # 默认超时300秒（流式请求更长）
            logger.info(f"[ChatCompletions-Stream] Starting streaming request, timeout={timeout}s")

            # 在生成器外部把 request.data 复制出来，避免在生成器执行期间访问已关闭的请求
            body = dict(request_data_copy)
            body['stream'] = True

            def generate():
                """生成器函数，按字节流式返回 SSE 数据，并解析 usage 用于结束后的统计/计费"""
                final_status = 0
                final_error_msg = ''
                final_usage = None
                # 累积未完成的 SSE 事件文本（用于解析 usage / [DONE]）
                sse_buffer = ''

                try:
                    with httpx.stream(
                        'POST',
                        target_url,
                        headers=headers,
                        json=body,
                        timeout=httpx.Timeout(timeout, connect=30.0, read=timeout),
                    ) as response:
                        final_status = response.status_code

                        if response.status_code >= 400:
                            try:
                                error_text = response.read().decode('utf-8', errors='replace')
                                error_data = json.loads(error_text)
                            except Exception:
                                error_data = {'error': {'message': 'Upstream error'}}

                            error_msg = error_data.get('error', {}).get('message', str(error_data))
                            final_error_msg = str(error_msg)
                            logger.error(
                                f"[ChatCompletions-Stream-Error] user_id={user.id}, account={account.name}, "
                                f"status={response.status_code}, response={error_data}"
                            )
                            yield (
                                'data: '
                                + json.dumps({
                                    'error': {
                                        'message': error_msg,
                                        'type': 'upstream_error',
                                        'code': f'http_{response.status_code}',
                                    }
                                })
                                + '\n\n'
                            ).encode('utf-8')
                            update_upstream_usage(account, success=False)
                            return

                        # 正常流式：原样按字节转发；同时累计字符串以解析 usage
                        for chunk in response.iter_raw():
                            if not chunk:
                                continue
                            # 立即转发给前端
                            yield chunk
                            # 解析 SSE 事件提取 usage（最后一个 chunk 通常带 usage）
                            try:
                                sse_buffer += chunk.decode('utf-8', errors='replace')
                            except Exception:
                                continue
                            while True:
                                idx = sse_buffer.find('\n\n')
                                if idx == -1:
                                    break
                                raw_event = sse_buffer[:idx]
                                sse_buffer = sse_buffer[idx + 2:]
                                for line in raw_event.split('\n'):
                                    line = line.strip()
                                    if not line.startswith('data:'):
                                        continue
                                    payload = line[5:].strip()
                                    if not payload or payload == '[DONE]':
                                        continue
                                    try:
                                        evt = json.loads(payload)
                                    except Exception:
                                        continue
                                    u = evt.get('usage') if isinstance(evt, dict) else None
                                    if isinstance(u, dict) and u:
                                        final_usage = u
                        update_upstream_usage(account, success=True)
                except httpx.TimeoutException:
                    update_upstream_usage(account, success=False)
                    final_status = 504
                    final_error_msg = 'Request timeout'
                    logger.error(f"[ChatCompletions-Stream-Timeout] user_id={user.id}, account={account.name}")
                    yield (
                        'data: '
                        + json.dumps({
                            'error': {
                                'message': 'Request timeout.',
                                'type': 'timeout_error',
                                'code': 'request_timeout',
                            }
                        })
                        + '\n\n'
                    ).encode('utf-8')
                except Exception as e:
                    update_upstream_usage(account, success=False)
                    final_status = 502
                    final_error_msg = str(e)
                    logger.error(
                        f"[ChatCompletions-Stream-Exception] user_id={user.id}, account={account.name}, error={str(e)}"
                    )
                    yield (
                        'data: '
                        + json.dumps({
                            'error': {
                                'message': str(e),
                                'type': 'server_error',
                                'code': 'internal_error',
                            }
                        })
                        + '\n\n'
                    ).encode('utf-8')
                finally:
                    # 流结束后：统一记录 APIAccessLog、更新 UsageLog、计费
                    response_time_ms = int((time.time() - start_time) * 1000)
                    prompt_tokens = 0
                    completion_tokens = 0
                    total_tokens = 0
                    cached_tokens = 0
                    if isinstance(final_usage, dict):
                        prompt_tokens = int(final_usage.get('prompt_tokens') or 0)
                        completion_tokens = int(final_usage.get('completion_tokens') or 0)
                        total_tokens = int(final_usage.get('total_tokens') or 0)
                        ptd = final_usage.get('prompt_tokens_details') or {}
                        if isinstance(ptd, dict):
                            cached_tokens = int(ptd.get('cached_tokens') or 0)
                        cached_tokens = cached_tokens or int(final_usage.get('cache_read_input_tokens') or 0)

                    # 更新 UsageLog
                    try:
                        usage_log.status_code = final_status or 200
                        usage_log.response_time = response_time_ms
                        usage_log.input_tokens = prompt_tokens
                        usage_log.output_tokens = completion_tokens
                        usage_log.total_tokens = total_tokens
                        usage_log.cached_tokens = cached_tokens
                        usage_log.save()
                    except Exception as e:
                        logger.error(f"[ChatCompletions-Stream] update usage_log failed: {e}")

                    # 计费（仅成功且有 token 数据时）：会把 cost 写回 usage_log
                    cost_value = 0
                    if (final_status and final_status < 400) and total_tokens > 0:
                        try:
                            cost_value, _ok = calculate_and_deduct_cost(
                                user, model_name,
                                prompt_tokens, completion_tokens, usage_log,
                                cached_tokens=cached_tokens,
                            )
                        except Exception as e:
                            logger.error(f"[ChatCompletions-Stream] charge failed: {e}")

                    # 写 APIAccessLog（带 token + cost）
                    try:
                        log_api_access(
                            api_key, user, 'POST', '/chat/completions',
                            request_data_copy,
                            final_usage if final_usage else (
                                {'error': {'message': final_error_msg}} if final_error_msg else {'streamed': True}
                            ),
                            final_status or 200,
                            response_time_ms,
                            client_ip,
                            model=model_obj,
                            upstream_account=account,
                            input_tokens=prompt_tokens,
                            output_tokens=completion_tokens,
                            total_tokens=total_tokens,
                            cached_tokens=cached_tokens,
                            cost=cost_value,
                        )
                    except Exception as e:
                        logger.error(f"[ChatCompletions-Stream] write access log failed: {e}")

            streaming_response = StreamingHttpResponse(
                generate(),
                content_type='text/event-stream; charset=utf-8',
            )
            streaming_response['Cache-Control'] = 'no-cache, no-transform'
            streaming_response['X-Accel-Buffering'] = 'no'  # 禁用 nginx/反代缓冲
            # 注意：'Connection' 是 hop-by-hop 头，由 WSGI 服务器控制；
            # Python 内置 wsgiref 会因应用层设置该头而 assert 失败，故不要在这里设置。
            streaming_response['X-Request-ID'] = str(usage_log.id)

            return streaming_response

        except httpx.TimeoutException:
            update_upstream_usage(account, success=False)
            return Response({
                'error': {
                    'message': 'Request timeout.',
                    'type': 'timeout_error',
                    'code': 'request_timeout'
                }
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)

        except Exception as e:
            update_upstream_usage(account, success=False)
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
    
    def _update_usage_log(self, log, response, response_data, response_time, model_code=''):
        """更新使用日志并执行计费"""
        log.response_time = response_time
        log.status_code = response.status_code

        cached_tokens = 0

        # 计算token使用量（如果有）
        if isinstance(response_data, dict):
            usage = response_data.get('usage', {}) or {}
            log.input_tokens = usage.get('prompt_tokens', 0) or 0
            log.output_tokens = usage.get('completion_tokens', 0) or 0
            log.total_tokens = usage.get('total_tokens', 0) or 0

            # 兼容多家上游的缓存命中字段
            ptd = usage.get('prompt_tokens_details') or {}
            if isinstance(ptd, dict):
                cached_tokens = int(ptd.get('cached_tokens') or 0)
            # Anthropic: cache_read_input_tokens
            cached_tokens = cached_tokens or int(usage.get('cache_read_input_tokens') or 0)

            if hasattr(response, 'headers'):
                log.response_body = str(response_data)[:5000]

        log.save()

        # 计费扣费（仅在请求成功时）
        if response.status_code < 400 and log.total_tokens > 0:
            cost, success = calculate_and_deduct_cost(
                log.user, model_code,
                log.input_tokens, log.output_tokens, log,
                cached_tokens=cached_tokens,
            )
            if not success and cost > 0:
                # 余额不足，记录警告但不影响响应
                pass


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
        
        # 选择上游账号
        account = select_upstream_account(model_name)
        if not account:
            return Response({
                'error': {
                    'message': f'Model {model_name} is not available.',
                    'type': 'invalid_request_error',
                    'code': 'model_not_found'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        logger.info(f"[Completions] model={model_name}, account={account.name}, base_url={account.base_url}")
        
        # 转发请求
        headers = {
            'Authorization': f'Bearer {account.api_key}',
            'Content-Type': 'application/json',
        }
        
        url = build_endpoint_url(account.base_url, 'completions')
        
        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(url, headers=headers, json=request.data)
            
            update_upstream_usage(account, success=response.status_code < 400)
            return Response(response.json(), status=response.status_code)
        except Exception as e:
            update_upstream_usage(account, success=False)
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
        
        # 选择上游账号
        account = select_upstream_account(model_name)
        if not account:
            return Response({
                'error': {
                    'message': f'Model {model_name} is not available or no upstream account configured.',
                    'code': 'model_not_found'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        logger.info(f"[Embeddings] model={model_name}, account={account.name}, base_url={account.base_url}")
        
        headers = {
            'Authorization': f'Bearer {account.api_key}',
            'Content-Type': 'application/json',
        }
        
        url = build_endpoint_url(account.base_url, 'embeddings')
        
        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(url, headers=headers, json=request.data)
            
            update_upstream_usage(account, success=response.status_code < 400)
            return Response(response.json(), status=response.status_code)
        except Exception as e:
            update_upstream_usage(account, success=False)
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
    renderer_classes = [JSONRenderer, EventStreamRenderer]
    
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
        elif path == 'responses':
            from .views_responses import ResponsesView
            responses_view = ResponsesView()
            return responses_view.post(request)
        else:
            return Response({
                'error': {
                    'message': f'Endpoint not found: /v1/{path}',
                    'type': 'invalid_request_error',
                    'code': 'not_found'
                }
            }, status=status.HTTP_404_NOT_FOUND)
