"""
Chat Completions 响应 → Response API 响应转换器（非流式）
"""
import json
import time
from typing import Any, Dict, List, Optional


def convert_response(chat_response: Dict[str, Any], original_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 Chat Completions 非流式响应转换为 Response API 响应。
    """
    chat_id = chat_response.get('id', '')
    resp_id = _convert_id(chat_id)
    created = chat_response.get('created', 0)
    model = chat_response.get('model', '')

    # 获取 finish_reason 和 message
    choices = chat_response.get('choices', [])
    choice = choices[0] if choices else {}
    message = choice.get('message', {}) if isinstance(choice, dict) else {}
    finish_reason = choice.get('finish_reason') if isinstance(choice, dict) else None

    # 构建 output
    output: List[Dict[str, Any]] = []
    if message:
        output_item = _build_output_item(message, resp_id, finish_reason)
        if output_item:
            output.append(output_item)

    # 状态映射
    status, incomplete_details = _map_finish_reason(finish_reason)

    # usage 转换
    usage = _convert_usage(chat_response.get('usage', {}) or {})

    return {
        'id': resp_id,
        'object': 'response',
        'created_at': created,
        'status': status,
        'error': None,
        'incomplete_details': incomplete_details,
        'instructions': original_request.get('instructions'),
        'max_output_tokens': original_request.get('max_output_tokens'),
        'model': model,
        'output': output,
        'parallel_tool_calls': original_request.get('parallel_tool_calls', True),
        'temperature': original_request.get('temperature', 1.0),
        'tool_choice': original_request.get('tool_choice', 'auto'),
        'tools': original_request.get('tools', []),
        'top_p': original_request.get('top_p', 1.0),
        'truncation': 'disabled',
        'usage': usage,
        'user': None,
        'metadata': original_request.get('metadata', {}),
    }


def anthropic_to_openai(resp: Dict[str, Any]) -> Dict[str, Any]:
    content_blocks = resp.get('content') or []
    text = ''.join(
        block.get('text', '')
        for block in content_blocks
        if isinstance(block, dict) and block.get('type') == 'text'
    )

    message: Dict[str, Any] = {
        'role': 'assistant',
        'content': text,
    }

    tool_calls = []
    for block in content_blocks:
        if not isinstance(block, dict) or block.get('type') != 'tool_use':
            continue
        tool_calls.append({
            'id': block.get('id'),
            'type': 'function',
            'function': {
                'name': block.get('name', ''),
                'arguments': json.dumps(block.get('input') or {}, ensure_ascii=False),
            },
        })

    if tool_calls:
        message['tool_calls'] = tool_calls

    usage = resp.get('usage') or {}
    input_tokens = int(usage.get('input_tokens') or 0)
    output_tokens = int(usage.get('output_tokens') or 0)

    return {
        'id': resp.get('id'),
        'object': 'chat.completion',
        'created': int(time.time()),
        'model': resp.get('model', ''),
        'choices': [{
            'index': 0,
            'message': message,
            'finish_reason': map_anthropic_stop_reason(resp.get('stop_reason')),
        }],
        'usage': {
            'prompt_tokens': input_tokens,
            'completion_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
        },
    }


def map_anthropic_stop_reason(stop_reason: Optional[str]) -> Optional[str]:
    return {
        'end_turn': 'stop',
        'max_tokens': 'length',
        'stop_sequence': 'stop',
        'tool_use': 'tool_calls',
    }.get(stop_reason)


def _convert_id(chat_id: str) -> str:
    """将 chatcmpl-xxx 转换为 resp-xxx"""
    if chat_id.startswith('chatcmpl-'):
        return chat_id.replace('chatcmpl-', 'resp-', 1)
    if chat_id.startswith('chatcmpl'):
        return chat_id.replace('chatcmpl', 'resp', 1)
    return f'resp_{chat_id}' if chat_id else 'resp_unknown'


def _build_output_item(message: Dict[str, Any], resp_id: str, finish_reason: Optional[str]) -> Optional[Dict[str, Any]]:
    """构建 Response API 的 output item（message 类型）"""
    role = message.get('role', 'assistant')
    content = message.get('content', '')
    tool_calls = message.get('tool_calls')

    item_id = f"msg_{resp_id.replace('resp-', '', 1).replace('resp_', '')}"

    output_item: Dict[str, Any] = {
        'type': 'message',
        'id': item_id,
        'status': 'completed' if finish_reason else 'in_progress',
        'role': role,
        'content': [],
    }

    # 处理 content
    if content:
        if isinstance(content, str):
            output_item['content'].append({
                'type': 'output_text',
                'text': content,
                'annotations': [],
            })
        elif isinstance(content, list):
            for part in content:
                converted = _convert_output_part(part)
                if converted:
                    output_item['content'].append(converted)

    # 处理 tool_calls
    if tool_calls:
        for tc in tool_calls:
            converted_tc = _convert_tool_call(tc)
            if converted_tc:
                output_item['content'].append(converted_tc)

    return output_item


def _convert_output_part(part: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """转换 assistant message 中的内容部分为 Response API 格式"""
    part_type = part.get('type')
    if part_type == 'text':
        return {'type': 'output_text', 'text': part.get('text', ''), 'annotations': []}
    # 其他类型直接透传
    return part


def _convert_tool_call(tc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    将 Chat API 的 tool_call 转换为 Response API 格式。

    Chat API:
        {"id": "call_xxx", "type": "function", "function": {"name": "...", "arguments": "{}"}}

    Response API:
        {"type": "tool_call", "id": "call_xxx", "call_type": "function",
         "status": "completed", "name": "...", "arguments": "{}"}
    """
    func = tc.get('function', {}) if isinstance(tc, dict) else {}
    return {
        'type': 'tool_call',
        'id': tc.get('id'),
        'call_type': tc.get('type', 'function'),
        'status': 'completed',
        'name': func.get('name', ''),
        'arguments': func.get('arguments', '{}'),
    }


def _map_finish_reason(finish_reason: Optional[str]) -> tuple:
    """
    将 Chat Completions 的 finish_reason 映射为 Response API 的 status。

    返回 (status, incomplete_details)
    """
    if finish_reason == 'stop' or finish_reason == 'tool_calls':
        return 'completed', None
    elif finish_reason == 'length':
        return 'incomplete', {'reason': 'max_output_tokens'}
    elif finish_reason == 'content_filter':
        return 'incomplete', {'reason': 'content_filter'}
    elif finish_reason is None:
        return 'in_progress', None
    else:
        # 未知 finish_reason，保守处理为 completed
        return 'completed', None


def _convert_usage(usage: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 Chat Completions 的 usage 转换为 Response API 格式。
    """
    prompt_tokens = usage.get('prompt_tokens', 0) or 0
    completion_tokens = usage.get('completion_tokens', 0) or 0
    total_tokens = usage.get('total_tokens', 0) or 0

    # 缓存 token 细节
    ptd = usage.get('prompt_tokens_details') or {}
    cached_tokens = 0
    if isinstance(ptd, dict):
        cached_tokens = int(ptd.get('cached_tokens') or 0)
    # Anthropic 兼容字段
    cached_tokens = cached_tokens or int(usage.get('cache_read_input_tokens') or 0)

    # 推理 token 细节
    ctd = usage.get('completion_tokens_details') or {}
    reasoning_tokens = 0
    if isinstance(ctd, dict):
        reasoning_tokens = int(ctd.get('reasoning_tokens') or 0)

    return {
        'input_tokens': prompt_tokens,
        'output_tokens': completion_tokens,
        'total_tokens': total_tokens,
        'input_tokens_details': {
            'cached_tokens': cached_tokens,
        },
        'output_tokens_details': {
            'reasoning_tokens': reasoning_tokens,
        },
    }
