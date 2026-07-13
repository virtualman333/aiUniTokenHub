from __future__ import annotations

from typing import Any, Dict, List, Tuple

import httpx


ANTHROPIC_VERSION = '2023-06-01'
ANTHROPIC_DEFAULT_BASE_URL = 'https://api.anthropic.com'


def protocol_of(channel: Any) -> str:
    return (getattr(channel, 'protocol', None) or 'openai').lower()


def endpoint_url(base_url: str, endpoint: str, protocol: str = 'openai') -> str:
    """
    构建 API 端点 URL
    直接拼接 base_url 和 endpoint，不自动添加 /v1
    用户需在配置 base_url 时包含完整路径（如 https://api.anthropic.com/v1）
    """
    if protocol == 'anthropic' and not base_url:
        base_url = f'{ANTHROPIC_DEFAULT_BASE_URL}/v1'

    base = (base_url or '').rstrip('/')
    endpoint = endpoint.strip('/')

    return f'{base}/{endpoint}'


def _anthropic_auth_headers(api_key: str) -> Dict[str, str]:
    """根据 Anthropic token 格式选择鉴权头。
    - sk-ant-oat01-... / sk-ant-sid-... (OAuth/会话 token) → Authorization: Bearer
    - 其他格式 → 两个头都带（x-api-key + Authorization: Bearer），由上游自行选择
    """
    if api_key.startswith('sk-ant-oat01-') or api_key.startswith('sk-ant-sid-'):
        return {'Authorization': f'Bearer {api_key}'}
    # 标准 API key 和中转 key：两个头都带，最大兼容
    return {
        'x-api-key': api_key,
        'Authorization': f'Bearer {api_key}',
    }


def headers_for(channel: Any, *, stream: bool = False) -> Dict[str, str]:
    protocol = protocol_of(channel)
    api_key = getattr(channel, 'api_key', '') or ''

    if protocol == 'anthropic':
        headers = {
            **_anthropic_auth_headers(api_key),
            'anthropic-version': ANTHROPIC_VERSION,
            'content-type': 'application/json',
        }
    else:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'content-type': 'application/json',
        }

    if stream:
        headers['Accept'] = 'text/event-stream'

    return headers


def test_connection(channel: Any, timeout: int = 10) -> httpx.Response:
    protocol = protocol_of(channel)
    if protocol == 'gemini':
        raise ValueError('Gemini protocol probing is not implemented yet')

    if protocol == 'anthropic':
        # Anthropic API 不一定支持 GET /v1/models，优先用 POST /v1/messages 做最小化鉴权测试
        return _test_anthropic_connection(channel, timeout)

    response = httpx.get(
        endpoint_url(getattr(channel, 'base_url', ''), 'models', protocol),
        headers=headers_for(channel),
        timeout=timeout,
    )
    return response


def _test_anthropic_connection(channel: Any, timeout: int = 10) -> httpx.Response:
    """Anthropic 专用连接测试：先尝试 POST /v1/messages（最小请求），失败则回退 GET /v1/models"""
    base_url = getattr(channel, 'base_url', '')
    headers = headers_for(channel, stream=False)
    # 发送最小 messages 请求（max_tokens=1 以极低成本验证鉴权）
    messages_url = endpoint_url(base_url, 'messages', 'anthropic')
    minimal_body = {
        'model': 'claude-3-haiku-20240307',
        'max_tokens': 1,
        'messages': [{'role': 'user', 'content': 'hi'}],
    }
    try:
        resp = httpx.post(messages_url, headers=headers, json=minimal_body, timeout=timeout)
        # 401/403 = 认证失败，直接返回
        if resp.status_code in (401, 403):
            return resp
        # 400/422 = 请求格式有误但认证通过，也算连接成功
        if resp.status_code in (400, 422):
            return resp
        # 2xx = 正常（虽然消耗了 1 token 但确认了连接）
        return resp
    except Exception:
        # POST 失败，回退到 GET /v1/models
        models_url = endpoint_url(base_url, 'models', 'anthropic')
        return httpx.get(models_url, headers=headers, timeout=timeout)


def fetch_models(channel: Any, timeout: int = 15) -> List[Dict[str, Any]]:
    protocol = protocol_of(channel)
    if protocol == 'gemini':
        raise ValueError('Gemini model sync is not implemented yet')

    if protocol == 'anthropic':
        return _fetch_anthropic_models(channel, timeout=timeout)

    response = httpx.get(
        endpoint_url(getattr(channel, 'base_url', ''), 'models', protocol),
        headers=headers_for(channel),
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get('data', []) if isinstance(payload, dict) else []
    return [item for item in data if isinstance(item, dict)]


def _fetch_anthropic_models(channel: Any, timeout: int = 15) -> List[Dict[str, Any]]:
    """获取 Anthropic 模型列表，优先尝试 GET /v1/models，失败则返回常用模型。
    认证错误 (401/403) 会直接抛出，避免返回假数据误导用户。"""
    url = endpoint_url(getattr(channel, 'base_url', ''), 'models', 'anthropic')
    headers = headers_for(channel, stream=False)
    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
        # 认证失败直接抛出，不吞错误
        if response.status_code in (401, 403):
            error_msg = _extract_error_message(response)
            raise httpx.HTTPStatusError(
                f'HTTP {response.status_code}: {error_msg}',
                request=response.request,
                response=response,
            )
        response.raise_for_status()
        payload = response.json()
        data = payload.get('data', []) if isinstance(payload, dict) else []
        return [
            {
                'id': item.get('id', ''),
                'display_name': item.get('display_name') or item.get('id', ''),
                'created_at': item.get('created_at'),
            }
            for item in data
            if isinstance(item, dict) and item.get('id')
        ]
    except httpx.HTTPStatusError:
        raise
    except Exception:
        # 代理不支持 GET /v1/models，返回常用 Anthropic 模型
        return [
            {'id': 'claude-3-5-sonnet-20241022', 'display_name': 'Claude 3.5 Sonnet'},
            {'id': 'claude-3-5-haiku-20241022', 'display_name': 'Claude 3.5 Haiku'},
            {'id': 'claude-3-opus-20240229', 'display_name': 'Claude 3 Opus'},
            {'id': 'claude-3-sonnet-20240229', 'display_name': 'Claude 3 Sonnet'},
            {'id': 'claude-3-haiku-20240307', 'display_name': 'Claude 3 Haiku'},
        ]


def _extract_error_message(response: httpx.Response) -> str:
    """从上游响应体中提取错误信息，用于排障。"""
    try:
        body = response.json()
        if isinstance(body, dict):
            # Anthropic 格式: {"error": {"message": "...", "type": "..."}}
            error = body.get('error')
            if isinstance(error, dict):
                return error.get('message') or error.get('type') or str(error)
            # OpenAI 格式: {"error": {"message": "..."}}
            msg = body.get('message') or body.get('msg')
            if msg:
                return str(msg)
        return response.text[:200]
    except Exception:
        return response.text[:200]


def probe_status(channel: Any, timeout: int = 10) -> Tuple[bool, str]:
    try:
        response = test_connection(channel, timeout=timeout)
        if response.status_code == 200:
            return True, ''
        # Anthropic 协议：400/422/404/405 表示连接正常（端点不支持或请求格式有误，非认证问题）
        protocol = protocol_of(channel)
        if protocol == 'anthropic' and response.status_code in (400, 404, 405, 422):
            return True, ''
        error_msg = _extract_error_message(response)
        return False, f'HTTP {response.status_code}: {error_msg}'
    except Exception as exc:
        return False, str(exc)[:500]
