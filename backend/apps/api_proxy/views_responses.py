"""
OpenAI Response API 适配视图

将 Response API 请求转换为 Chat Completions 请求转发给上游，
然后将上游的 Chat Completions 响应转换回 Response API 格式返回给客户端。

支持：
- 非流式（stream=false）
- 流式（stream=true，SSE）
"""
import json
import time
import logging
from typing import Any, Dict

import httpx
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from django.http import StreamingHttpResponse

from apps.users.models import APIKey, UsageLog
from apps.ai_models.models import AIModel
from apps.ai_models.upstream_models import UpstreamAccount
from .models import APIAccessLog
from .views_openai import (
    get_api_key_from_request,
    select_upstream_account,
    check_rate_limit,
    update_upstream_usage,
    update_usage_log,
    log_api_access,
    calculate_and_deduct_cost,
    get_client_ip,
    build_endpoint_url,
    build_protocol_endpoint_url,
    EventStreamRenderer,
)
from .adapters.request_adapter import convert_request as convert_req_to_chat, openai_to_anthropic
from .adapters.response_adapter import convert_response as convert_resp_to_response, anthropic_to_openai
from .adapters.streaming_adapter import AnthropicStreamToOpenAIConverter, IncrementalUtf8Decoder, StreamingConverter
from .adapters.upstream_body import build_stream_body
from .channel_probes import ANTHROPIC_VERSION, protocol_of
# 计费结果语义 / 文案 / 状态码只从这一处来。这个文件此前也自己写着
# '余额不足，请充值后再试。'，并把服务端扣费出错回成同一句话。
from apps.utils.billing import (
    CHAT_ERROR_TYPE,
    DEDUCT_OK,
    DEDUCT_ERROR,
    deduct_failure_payload,
    parse_usage_dict,
    precheck_failure,
    unbilled_stream_note,
)

logger = logging.getLogger('api_proxy')


class ResponsesView(APIView):
    """
    OpenAI Response API 适配端点
    POST /v1/responses
    """
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer, EventStreamRenderer]

    def post(self, request):
        return self._handle_responses(request)

    # ------------------------------------------------------------------
    # 主处理逻辑
    # ------------------------------------------------------------------

    def _handle_responses(self, request):
        start_time = time.time()

        # 1. 获取模型名称
        model_name = request.data.get('model')
        if not model_name:
            return self._error_response(
                'Missing required parameter: model',
                'invalid_request_error',
                'missing_required_parameter',
                param='model',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 2. 验证 API Key
        api_key, user = get_api_key_from_request(request)
        if not api_key:
            return self._error_response(
                'Incorrect API key provided.',
                'authentication_error',
                'invalid_api_key',
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        # 3. 检查用户状态
        if not user.is_active:
            return self._error_response(
                'User account is disabled.',
                'authentication_error',
                'user_disabled',
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        # 4. 检查 API Key 额度
        if api_key.remaining_calls is not None and api_key.remaining_calls <= 0:
            return self._error_response(
                'API key quota exceeded.',
                'rate_limit_error',
                'quota_exceeded',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # 5. 选择上游账号
        account = select_upstream_account(model_name)
        if not account:
            return self._error_response(
                f'Model {model_name} is not available or no upstream account configured.',
                'invalid_request_error',
                'model_not_found',
                param='model',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 6. 检查速率限制
        rate_limit_error = check_rate_limit(api_key, account)
        if rate_limit_error:
            return rate_limit_error

        # 7. 转换请求格式（Response API → Chat Completions）
        try:
            original_request = self._copy_request_data(request)
            chat_request = convert_req_to_chat(original_request)
        except Exception as e:
            logger.error(f"[Responses] Request conversion failed: {e}")
            return self._error_response(
                f'Request conversion error: {str(e)}',
                'invalid_request_error',
                'conversion_error',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"[Responses] model={model_name}, user={user.id}, account={account.name}")
        logger.info(f"[Responses] Account base_url: {account.base_url}")
        logger.info(f"[Responses] Original request body: {json.dumps(original_request, ensure_ascii=False)}")
        logger.info(f"[Responses] Converted Chat request: {json.dumps(chat_request, ensure_ascii=False)}")

        # 余额校验：余额为 0 或负数时拒绝，避免消耗上游成本并阻止透支扩大
        if user.balance <= 0:
            logger.warning(
                f"[Responses] 用户 {user.username}(ID:{user.id}) 余额不足"
                f"(余额:{user.balance})，拒绝请求"
            )
            # 这里是**真的**余额不足（按 balance<=0 判的），文案/ code / 状态码由
            # billing 统一给 —— 与扣费失败那条分支不同，那条不能说这四个字。
            msg, code, http_status = precheck_failure(user.balance)
            return self._error_response(msg, CHAT_ERROR_TYPE, code, status_code=http_status)

        # 8. 分流式 / 非流式
        is_streaming = original_request.get('stream', False)

        if is_streaming:
            return self._handle_streaming(
                original_request, chat_request, api_key, user,
                account, model_name, start_time, request,
            )
        else:
            return self._handle_normal(
                original_request, chat_request, api_key, user,
                account, model_name, start_time, request,
            )

    # ------------------------------------------------------------------
    # 非流式处理
    # ------------------------------------------------------------------

    def _handle_normal(self, original_request, chat_request, api_key, user,
                       account, model_name, start_time, request):
        model_obj = AIModel.objects.filter(code=model_name).first()
        protocol = protocol_of(account)

        headers = self._build_headers()
        if protocol == 'anthropic':
            headers.update({
                'x-api-key': account.api_key,
                'anthropic-version': ANTHROPIC_VERSION,
            })
            upstream_body = openai_to_anthropic(chat_request, model_name)
        else:
            headers['Authorization'] = f'Bearer {account.api_key}'
            upstream_body = chat_request
        target_url = build_protocol_endpoint_url(
            account.base_url,
            'messages' if protocol == 'anthropic' else 'chat/completions',
            protocol,
        )

        usage_log = UsageLog.objects.create(
            user=user,
            api_key=api_key,
            method='POST',
            endpoint='/responses',
        )

        logger.info(f"[Responses-Normal] Forwarding to: {target_url}")

        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(target_url, headers=headers, json=upstream_body)

            response_time = int((time.time() - start_time) * 1000)

            # 解析上游响应
            try:
                response_data = response.json()
            except Exception:
                # 尝试解码可能的压缩响应
                try:
                    import gzip
                    decompressed = gzip.decompress(response.content)
                    response_data = json.loads(decompressed.decode('utf-8'))
                except Exception:
                    # 降级为原始文本（截断以避免过大）
                    raw_text = response.text[:2000] if response.text else '<empty response>'
                    response_data = {'raw_response': raw_text}

            # 转换响应格式（Chat → Response）
            if response.status_code < 400:
                try:
                    if protocol == 'anthropic':
                        response_data = anthropic_to_openai(response_data)
                    response_data = convert_resp_to_response(response_data, original_request)
                except Exception as e:
                    logger.error(f"[Responses] Response conversion failed: {e}")
            else:
                # 错误响应包装为 Response API 格式
                logger.error(
                    f"[Responses-Normal-Error] user_id={user.id}, account={account.name}, "
                    f"target_url={target_url}, status={response.status_code}, "
                    f"response_body={response_data}"
                )
                response_data = self._wrap_error(response_data, response.status_code)

            # 更新日志与计费。返回值是 (状态, 金额)：状态是三档而不是布尔值 ——
            # 布尔值会把「余额不足」与「服务端出错」压成同一句话。
            billing_status, billing_cost = update_usage_log(
                usage_log, response, response_data, response_time, model_name,
                upstream_account=account)
            usage_log.refresh_from_db()
            update_upstream_usage(account, success=response.status_code < 400)

            # 扣费没成功且这一笔本该收费：上游成本已花、用户也拿到了回答，但账没记上。
            # 这是平台的问题（余额不足在扣费这一步不可能发生，见
            # calculate_and_deduct_cost 的说明），必须回 5xx 且文案里不能提余额。
            if (billing_status == DEDUCT_ERROR and billing_cost > 0
                    and response.status_code < 400):
                msg, code, http_status = deduct_failure_payload(
                    billing_status, billing_cost, user.balance)
                logger.error(
                    f"[Responses] 扣费未成功，按服务端故障回 {http_status} "
                    f"user_id={user.id} cost={billing_cost} status={billing_status}"
                )
                return self._error_response(msg, CHAT_ERROR_TYPE, code, status_code=http_status)

            # 记录访问日志
            self._log_access(
                api_key, user, original_request, response_data,
                response.status_code, response_time,
                model_obj, account, usage_log, request,
            )

            return Response(response_data, status=response.status_code)

        except httpx.TimeoutException:
            logger.error(f"[Responses-Normal-Timeout] user_id={user.id}, account={account.name}")
            update_upstream_usage(account, success=False)
            return self._error_response(
                'Request timeout. Please try again.',
                'timeout_error',
                'request_timeout',
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        except Exception as e:
            logger.error(f"[Responses-Normal-Exception] user_id={user.id}, account={account.name}, error={str(e)}")
            update_upstream_usage(account, success=False)
            return self._error_response(
                f'Internal server error: {str(e)}',
                'server_error',
                'internal_error',
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

    # ------------------------------------------------------------------
    # 流式处理
    # ------------------------------------------------------------------

    def _handle_streaming(self, original_request, chat_request, api_key, user,
                          account, model_name, start_time, request):
        # 检查余额是否充足，余额为0或负数时拒绝请求
        if user.balance <= 0:
            logger.warning(f"[Responses-Stream] 用户 {user.username}(ID:{user.id}) 余额为0，拒绝流式请求")
            msg, code, http_status = precheck_failure(user.balance)
            return self._error_response(msg, CHAT_ERROR_TYPE, code, status_code=http_status)
        
        protocol = protocol_of(account)
        headers = self._build_headers()
        if protocol == 'anthropic':
            headers.update({
                'x-api-key': account.api_key,
                'anthropic-version': ANTHROPIC_VERSION,
            })
        else:
            headers['Authorization'] = f'Bearer {account.api_key}'
        headers['Accept'] = 'text/event-stream'
        headers.pop('Accept-Encoding', None)
        headers.pop('accept-encoding', None)

        target_url = build_protocol_endpoint_url(
            account.base_url,
            'messages' if protocol == 'anthropic' else 'chat/completions',
            protocol,
        )

        client_ip = get_client_ip(request)
        model_obj = AIModel.objects.filter(code=model_name).first()

        usage_log = UsageLog.objects.create(
            user=user,
            api_key=api_key,
            method='POST',
            endpoint='/responses',
        )

        logger.info(f"[Responses-Stream] Forwarding to: {target_url}")

        try:
            # 同 /v1/chat/completions：流式请求体只有一处拼装逻辑，见
            # adapters/upstream_body.py（它负责向上游索取 usage）。
            body = build_stream_body(chat_request, protocol, model_name)
            logger.debug(f"[Responses-Stream] Request body: {body}")

            def generate():
                converter = StreamingConverter()
                anthropic_converter = AnthropicStreamToOpenAIConverter(model_name) if protocol == 'anthropic' else None
                final_status = 0
                final_error_msg = ''
                final_usage = None
                sse_buffer = ''
                # 增量解码：网络分片会落在多字节字符（中文/emoji）中间，
                # 直接 chunk.decode(..., errors='replace') 会把一个汉字替换成三个 �，
                # 进而让后面的事件 JSON 解析失败、usage 丢失（漏计费）。
                sse_decoder = IncrementalUtf8Decoder()

                try:
                    with httpx.stream(
                        'POST',
                        target_url,
                        headers=headers,
                        json=body,
                        timeout=httpx.Timeout(300, connect=30.0, read=300),
                    ) as response:
                        final_status = response.status_code

                        # 上游错误
                        if response.status_code >= 400:
                            error_text = ''
                            error_data: Dict[str, Any] = {}
                            try:
                                error_text = response.read().decode('utf-8', errors='replace')
                                if error_text.strip():
                                    error_data = json.loads(error_text)
                            except Exception:
                                # JSON 解析失败，保留原始文本
                                if not error_text.strip():
                                    error_text = '<empty response body>'
                                error_data = {'raw': error_text}

                            # 提取错误消息（兼容多种上游格式）
                            error_msg = 'Upstream error'
                            if isinstance(error_data, dict):
                                if 'error' in error_data:
                                    err_obj = error_data['error']
                                    if isinstance(err_obj, dict):
                                        error_msg = err_obj.get('message', str(err_obj))
                                    else:
                                        error_msg = str(err_obj)
                                elif 'message' in error_data:
                                    error_msg = error_data['message']
                                elif 'detail' in error_data:
                                    error_msg = error_data['detail']
                                elif 'raw' in error_data:
                                    error_msg = error_data['raw'][:500]

                            final_error_msg = str(error_msg)
                            logger.error(
                                f"[Responses-Stream-Error] user_id={user.id}, account={account.name}, "
                                f"target_url={target_url}, status={response.status_code}, "
                                f"error_msg={error_msg}, raw_body={error_data}"
                            )
                            yield self._error_sse('error', error_msg, f'http_{response.status_code}')
                            update_upstream_usage(account, success=False)
                            return

                        # 正常流式：逐 chunk 转换并转发
                        for chunk in response.iter_raw():
                            if not chunk:
                                continue

                            # SSE 格式转换
                            if anthropic_converter is not None:
                                for openai_event in anthropic_converter.feed(chunk):
                                    events = converter.feed(openai_event.encode('utf-8'))
                                    for event_line in events:
                                        yield event_line.encode('utf-8')
                                final_usage = anthropic_converter.usage
                                continue

                            events = converter.feed(chunk)
                            for event_line in events:
                                yield event_line.encode('utf-8')

                            # 解析 usage（用于结束后计费）
                            try:
                                sse_buffer += sse_decoder.decode(chunk)
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

                        # 确保流式结束事件已发送
                        finish_events = converter.finish()
                        if anthropic_converter is not None:
                            for openai_event in anthropic_converter.finish():
                                events = converter.feed(openai_event.encode('utf-8'))
                                for event_line in events:
                                    yield event_line.encode('utf-8')
                            final_usage = anthropic_converter.usage
                        for event_line in finish_events:
                            yield event_line.encode('utf-8')

                        update_upstream_usage(account, success=True)

                except httpx.TimeoutException:
                    logger.error(f"[Responses-Stream-Timeout] user_id={user.id}, account={account.name}")
                    update_upstream_usage(account, success=False)
                    final_status = 504
                    final_error_msg = 'Request timeout'
                    yield self._error_sse('error', 'Request timeout.', 'request_timeout')

                except Exception as e:
                    logger.error(f"[Responses-Stream-Exception] user_id={user.id}, account={account.name}, error={str(e)}")
                    update_upstream_usage(account, success=False)
                    final_status = 502
                    final_error_msg = str(e)
                    yield self._error_sse('error', str(e), 'internal_error')

                finally:
                    # 流结束后：更新 UsageLog、计费、记录访问日志
                    self._finalize_stream(
                        usage_log, user, api_key, model_name,
                        original_request, final_status, final_error_msg,
                        final_usage, start_time, client_ip, model_obj, account,
                    )

            streaming_response = StreamingHttpResponse(
                generate(),
                content_type='text/event-stream; charset=utf-8',
            )
            streaming_response['Cache-Control'] = 'no-cache, no-transform'
            streaming_response['X-Accel-Buffering'] = 'no'
            streaming_response['X-Request-ID'] = str(usage_log.id)

            return streaming_response

        except Exception as e:
            update_upstream_usage(account, success=False)
            return self._error_response(
                f'Internal server error: {str(e)}',
                'server_error',
                'internal_error',
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _build_headers(self) -> Dict[str, str]:
        """构建转发到上游的请求头"""
        return {'Content-Type': 'application/json'}

    def _copy_request_data(self, request) -> Dict[str, Any]:
        """安全复制请求数据"""
        if hasattr(request.data, 'items'):
            return {k: v for k, v in request.data.items()}
        return dict(request.data or {})

    def _error_response(self, message, error_type, code,
                        param=None, status_code=status.HTTP_400_BAD_REQUEST):
        """构造 Response API 格式的错误响应"""
        payload: Dict[str, Any] = {
            'error': {
                'message': message,
                'type': error_type,
                'code': code,
            }
        }
        if param is not None:
            payload['error']['param'] = param
        return Response(payload, status=status_code)

    def _wrap_error(self, response_data: Any, http_status: int) -> Dict[str, Any]:
        """将上游错误响应包装为 Response API 格式，同时保留原始错误信息"""
        original = response_data if isinstance(response_data, dict) else {'raw': str(response_data)}

        # 从各种上游格式中提取错误消息
        msg = 'Upstream error'
        err_type = 'upstream_error'
        code = f'http_{http_status}'

        if isinstance(response_data, dict):
            # 标准 OpenAI 格式: {"error": {"message": "...", "type": "...", "code": "..."}}
            if 'error' in response_data:
                upstream_error = response_data['error']
                if isinstance(upstream_error, dict):
                    msg = upstream_error.get('message', str(upstream_error))
                    err_type = upstream_error.get('type', 'upstream_error')
                    code = upstream_error.get('code', f'http_{http_status}')
                else:
                    msg = str(upstream_error)
            # FastAPI/DRF 格式: {"detail": "..."}
            elif 'detail' in response_data:
                msg = response_data['detail']
            # 其他格式: {"message": "..."}
            elif 'message' in response_data:
                msg = response_data['message']
            # 原始文本 fallback
            elif 'raw_response' in response_data:
                raw = response_data['raw_response']
                msg = str(raw)[:500] if raw else 'Upstream returned empty response'
        else:
            msg = str(response_data)[:500]

        return {
            'error': {
                'message': msg,
                'type': err_type,
                'code': code,
                'original_response': original,
            }
        }

    def _error_sse(self, event_type: str, message: str, code: str):
        """构造 Response API 格式的错误 SSE 事件"""
        data = {
            'type': event_type,
            'error': {
                'message': message,
                'type': 'upstream_error' if event_type == 'error' else 'server_error',
                'code': code,
            }
        }
        return (f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n").encode('utf-8')

    # ------------------------------------------------------------------
    # 日志 & 计费
    # ------------------------------------------------------------------

    def _finalize_stream(self, usage_log, user, api_key, model_name,
                         original_request, final_status, final_error_msg,
                         final_usage, start_time, client_ip, model_obj, account):
        """流式结束后统一记录日志和计费"""
        response_time_ms = int((time.time() - start_time) * 1000)

        # 用量解析只有一处（`apps/utils/billing.parse_usage_dict`），这里以前
        # 自己写了一份 —— 而它不认 Responses 形态的 `input_tokens` 与
        # `input_tokens_details`。同一个上游换个端点算出不同用量，收的钱就不同。
        prompt_tokens, completion_tokens, total_tokens, cached_tokens = parse_usage_dict(final_usage)

        # 成功却一个 token 都没收到 = 这笔没收钱。与 /chat/completions 同一个
        # 判据、同一句话（apps/utils/billing.py），两边不许各写一份。
        note = unbilled_stream_note(
            '/responses', final_status, total_tokens,
            user_id=getattr(user, 'id', None), usage_log_id=getattr(usage_log, 'id', None),
        )
        if note:
            logger.warning(note)

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
            logger.error(f"[Responses-Stream] update usage_log failed: {e}")

        # 计费
        cost_value = 0
        if (final_status and final_status < 400) and total_tokens > 0:
            try:
                cost_value, charge_status = calculate_and_deduct_cost(
                    user, model_name,
                    prompt_tokens, completion_tokens, usage_log,
                    cached_tokens=cached_tokens,
                    upstream_account=account,
                )
                if charge_status != DEDUCT_OK:
                    # 流式响应头已经发出去了，改不了 HTTP 状态码 —— 只能如实记日志
                    # （带金额，好对账）。这条路径上的失败同样是服务端问题。
                    logger.error(
                        f"[Responses-Stream] 扣费未成功（服务端） "
                        f"user_id={user.id} cost={cost_value} status={charge_status}"
                    )
            except Exception as e:
                logger.error(f"[Responses-Stream] charge failed: {e}")

        # 记录访问日志
        try:
            usage_log.refresh_from_db()
            log_api_access(
                api_key, user, 'POST', '/responses',
                original_request,
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
                upstream_cost=usage_log.upstream_cost,
                profit=usage_log.profit,
            )
        except Exception as e:
            logger.error(f"[Responses-Stream] write access log failed: {e}")

    def _log_access(self, api_key, user, request_body, response_data,
                    status_code, response_time, model_obj, account,
                    usage_log, request):
        """记录非流式的 API 访问日志"""
        try:
            log_api_access(
                api_key, user, 'POST', '/responses',
                request_body, response_data, status_code,
                response_time, get_client_ip(request),
                model=model_obj, upstream_account=account,
                input_tokens=usage_log.input_tokens,
                output_tokens=usage_log.output_tokens,
                total_tokens=usage_log.total_tokens,
                cached_tokens=usage_log.cached_tokens,
                cost=usage_log.cost,
                upstream_cost=usage_log.upstream_cost,
                profit=usage_log.profit,
            )
        except Exception:
            pass
