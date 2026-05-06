"""
Response API 请求 → Chat Completions 请求转换器
"""
from typing import Any, Dict, List, Optional


def convert_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 OpenAI Response API 请求体转换为 Chat Completions API 请求体。

    核心转换：
    - input + instructions → messages
    - max_output_tokens → max_tokens
    - tools 扁平格式 → 嵌套 function 格式
    - developer → system 角色
    - input_text/input_image → text/image_url 内容类型
    - reasoning.effort → reasoning_effort
    """
    chat_data: Dict[str, Any] = {}

    # model 直接透传
    chat_data['model'] = data.get('model')

    # 构建 messages
    messages: List[Dict[str, Any]] = []

    # instructions → system message（放在最前面）
    instructions = data.get('instructions')
    if instructions:
        messages.append({'role': 'system', 'content': instructions})

    # input 处理
    input_data = data.get('input')
    if isinstance(input_data, str):
        messages.append({'role': 'user', 'content': input_data})
    elif isinstance(input_data, list):
        for item in input_data:
            msg = _convert_input_item(item)
            if msg is not None:
                messages.append(msg)

    chat_data['messages'] = messages

    # 简单参数直接透传
    _PASS_THROUGH_KEYS = [
        'stream', 'temperature', 'top_p', 'presence_penalty',
        'frequency_penalty', 'stop', 'seed', 'tool_choice',
        'parallel_tool_calls', 'response_format',
    ]
    for key in _PASS_THROUGH_KEYS:
        if key in data:
            chat_data[key] = data[key]

    # max_output_tokens → max_tokens
    if 'max_output_tokens' in data:
        chat_data['max_tokens'] = data['max_output_tokens']

    # tools 格式转换
    if 'tools' in data:
        chat_data['tools'] = _convert_tools(data['tools'])

    # reasoning → reasoning_effort（仅 o1/o3 系列）
    reasoning = data.get('reasoning')
    if isinstance(reasoning, dict):
        chat_data['reasoning_effort'] = reasoning.get('effort', 'medium')

    return chat_data


def _convert_input_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    将 Response API 的 input item 转换为 Chat API 的 message。

    支持的 item type：
    - "message": 普通对话消息
    - 无 type 但有 role: 也按 message 处理（某些客户端省略 type 字段）
    - "function_call_output": 工具调用结果
    """
    item_type = item.get('type')

    # 有 role 字段但无 type（或 type 为 message），都按 message 处理
    has_role = 'role' in item
    is_message = (item_type == 'message') or (item_type is None and has_role)

    if is_message:
        role = item.get('role', 'user')
        # Response API 用 developer 替代 system
        if role == 'developer':
            role = 'system'

        content = item.get('content')

        # 多模态内容转换
        if isinstance(content, list):
            converted_content: List[Dict[str, Any]] = []
            all_text_only = True
            has_image = False
            for part in content:
                converted_part = _convert_content_part(part)
                if converted_part is not None:
                    converted_content.append(converted_part)
                    # 检查是否包含图片（非纯文本）
                    if converted_part.get('type') == 'image_url':
                        has_image = True
                        all_text_only = False
                    elif converted_part.get('type') != 'text':
                        all_text_only = False
                else:
                    all_text_only = False

            # 如果 content 里全是纯文本（没有图片），合并为纯文本字符串
            # 很多上游只接受纯字符串格式的 content，不支持数组
            if all_text_only and converted_content and not has_image:
                texts = [p.get('text', '') for p in converted_content]
                content = ''.join(texts)
            else:
                content = converted_content

        return {'role': role, 'content': content}

    elif item_type == 'function_call_output':
        # Response API 的 tool 结果 → Chat API 的 tool message
        return {
            'role': 'tool',
            'tool_call_id': item.get('call_id'),
            'content': item.get('output', ''),
        }

    # 不认识的类型，跳过
    return None


def _convert_content_part(part: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    转换多模态内容部分。

    Response API → Chat Completions：
    - input_text → text
    - input_image → image_url
    - output_text → text（用于 assistant message 历史回传）
    """
    part_type = part.get('type')

    if part_type == 'input_text':
        return {'type': 'text', 'text': part.get('text', '')}

    elif part_type == 'output_text':
        # Response API 的 output_text（assistant 输出）→ Chat API 的 text
        return {'type': 'text', 'text': part.get('text', '')}

    elif part_type == 'input_image':
        image_url = part.get('image_url', '')
        # 兼容字符串和 dict 两种形式
        if isinstance(image_url, dict):
            image_url = image_url.get('url', '')
        return {
            'type': 'image_url',
            'image_url': {'url': image_url},
        }

    # 未知类型直接透传，让上游决定能否处理
    return part


def _convert_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    转换工具定义格式。

    Response API 扁平格式：
        {"type": "function", "name": "...", "description": "...", "parameters": {...}}

    Chat Completions 嵌套格式：
        {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
    """
    converted: List[Dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue

        # 已经是 Chat API 嵌套格式，直接透传
        if 'function' in tool:
            converted.append(tool)
            continue

        # Response API 扁平格式，包装为嵌套格式
        converted.append({
            'type': tool.get('type', 'function'),
            'function': {
                'name': tool.get('name', ''),
                'description': tool.get('description', ''),
                'parameters': tool.get('parameters', {}),
            }
        })

    return converted
