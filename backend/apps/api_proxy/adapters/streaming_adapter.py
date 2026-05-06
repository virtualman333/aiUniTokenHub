"""
流式 SSE 转换器：Chat Completions SSE → Response API SSE

在生成器内部维护状态机，逐 chunk 解析上游 SSE 事件并转换为 Response API 格式。
"""
import json
import re
from typing import Any, Dict, List, Optional


class StreamingConverter:
    """
    流式 SSE 转换器。

    状态机：
        IDLE → CREATED → OUTPUT_ITEM → CONTENT_PART → DELTA → DONE → COMPLETED
    """

    def __init__(self) -> None:
        self.initialized = False
        self.output_item_added = False
        self.content_part_added = False
        self.text_done = False
        self.output_item_done = False
        self.completed = False

        self.resp_id = ''
        self.msg_id = ''
        self.model = ''
        self.created = 0
        self.message_role = 'assistant'

        self.full_text = ''
        self.tool_calls: Dict[int, Dict[str, Any]] = {}
        self.sse_buffer = ''
        self.usage: Dict[str, Any] = {}

    def feed(self, chunk: bytes) -> List[str]:
        """
        接收上游 SSE chunk，返回转换后的 Response API SSE 事件行列表。
        """
        events: List[str] = []

        try:
            self.sse_buffer += chunk.decode('utf-8', errors='replace')
        except Exception:
            return events

        # 兼容 \n\n 与 \r\n\r\n
        while True:
            match = re.search(r'\r?\n\r?\n', self.sse_buffer)
            if match is None:
                break

            raw_event = self.sse_buffer[:match.start()]
            self.sse_buffer = self.sse_buffer[match.end():]

            data_lines: List[str] = []
            for line in raw_event.splitlines():
                line = line.strip()
                if line.startswith('data:'):
                    data_lines.append(line[5:].strip())

            if not data_lines:
                continue

            payload = '\n'.join(data_lines).strip()
            if payload == '[DONE]':
                events.extend(self._finish())
                continue

            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue

            events.extend(self._process_chunk(data))

        return events

    def _ensure_initialized(self, data: Dict[str, Any]) -> List[str]:
        events: List[str] = []
        if self.initialized:
            return events

        self.initialized = True
        chat_id = data.get('id', '')
        self.resp_id = _convert_id(chat_id)
        self.msg_id = f"msg_{self.resp_id.replace('resp-', '', 1).replace('resp_', '')}"
        self.model = data.get('model', self.model)
        self.created = data.get('created', 0)

        events.append(_sse_event('response.created', {
            'response': _build_response_stub(self.resp_id, self.created, 'in_progress', self.model)
        }))
        events.append(_sse_event('response.in_progress', {
            'response': {
                'id': self.resp_id,
                'object': 'response',
                'status': 'in_progress',
            }
        }))
        return events

    def _ensure_message_item(self, role: Optional[str] = None) -> List[str]:
        events: List[str] = []
        if self.output_item_added:
            return events

        role = role or self.message_role
        self.output_item_added = True
        events.append(_sse_event('response.output_item.added', {
            'output_index': 0,
            'item': {
                'type': 'message',
                'id': self.msg_id,
                'status': 'in_progress',
                'role': role,
                'content': [],
            }
        }))
        return events

    def _ensure_content_part(self) -> List[str]:
        events: List[str] = []
        if self.content_part_added:
            return events

        self.content_part_added = True
        events.extend(self._ensure_message_item())
        events.append(_sse_event('response.content_part.added', {
            'item_id': self.msg_id,
            'output_index': 0,
            'content_index': 0,
            'part': {
                'type': 'output_text',
                'text': '',
                'annotations': [],
            }
        }))
        return events

    def _tool_output_index(self, tool_index: int) -> int:
        return (1 if self.output_item_added else 0) + tool_index

    def _tool_item_id(self, call_id: Optional[str], index: int) -> str:
        if call_id:
            return f"fc_{call_id.replace('call_', '', 1)}"
        suffix = self.resp_id.replace('resp-', '', 1).replace('resp_', '') or 'unknown'
        return f"fc_{suffix}_{index}"

    def _process_tool_call_delta(self, tc: Dict[str, Any]) -> List[str]:
        events: List[str] = []
        idx = tc.get('index', 0)
        if not isinstance(idx, int):
            idx = 0

        if idx not in self.tool_calls:
            self.tool_calls[idx] = {
                'id': None,
                'item_id': None,
                'name': '',
                'arguments': '',
                'added': False,
            }

        entry = self.tool_calls[idx]
        if tc.get('id'):
            entry['id'] = tc['id']

        func = tc.get('function', {}) or {}
        if func.get('name'):
            entry['name'] = func['name']

        if not entry['item_id']:
            entry['item_id'] = self._tool_item_id(entry.get('id'), idx)

        output_index = self._tool_output_index(idx)

        if not entry['added']:
            entry['added'] = True
            events.append(_sse_event('response.output_item.added', {
                'output_index': output_index,
                'item': {
                    'type': 'function_call',
                    'id': entry['item_id'],
                    'call_id': entry['id'],
                    'status': 'in_progress',
                    'name': entry['name'],
                    'arguments': '',
                }
            }))

        arg_delta = func.get('arguments')
        if arg_delta:
            entry['arguments'] += arg_delta
            events.append(_sse_event('response.function_call_arguments.delta', {
                'item_id': entry['item_id'],
                'output_index': output_index,
                'delta': arg_delta,
            }))

        return events

    def _finish_text_events(self) -> List[str]:
        events: List[str] = []
        if self.content_part_added and not self.text_done:
            self.text_done = True
            events.append(_sse_event('response.output_text.done', {
                'item_id': self.msg_id,
                'output_index': 0,
                'content_index': 0,
                'text': self.full_text,
            }))
            events.append(_sse_event('response.content_part.done', {
                'item_id': self.msg_id,
                'output_index': 0,
                'content_index': 0,
                'part': {
                    'type': 'output_text',
                    'text': self.full_text,
                    'annotations': [],
                }
            }))
        return events

    def _finish_tool_events(self) -> List[str]:
        events: List[str] = []
        for idx, tc in sorted(self.tool_calls.items()):
            if not tc.get('added'):
                continue

            output_index = self._tool_output_index(idx)
            events.append(_sse_event('response.function_call_arguments.done', {
                'item_id': tc['item_id'],
                'output_index': output_index,
                'arguments': tc['arguments'],
            }))
            events.append(_sse_event('response.output_item.done', {
                'output_index': output_index,
                'item': {
                    'type': 'function_call',
                    'id': tc['item_id'],
                    'call_id': tc['id'],
                    'status': 'completed',
                    'name': tc['name'],
                    'arguments': tc['arguments'],
                }
            }))
        return events

    def _build_output(self) -> List[Dict[str, Any]]:
        output: List[Dict[str, Any]] = []

        if self.content_part_added:
            output.append({
                'type': 'message',
                'id': self.msg_id,
                'status': 'completed',
                'role': self.message_role,
                'content': [
                    {
                        'type': 'output_text',
                        'text': self.full_text,
                        'annotations': [],
                    }
                ],
            })

        for _, tc in sorted(self.tool_calls.items()):
            if not tc.get('added'):
                continue
            output.append({
                'type': 'function_call',
                'id': tc['item_id'],
                'call_id': tc['id'],
                'status': 'completed',
                'name': tc['name'],
                'arguments': tc['arguments'],
            })

        return output

    def _build_usage(self) -> Dict[str, Any]:
        prompt_tokens = int(self.usage.get('prompt_tokens') or 0)
        completion_tokens = int(self.usage.get('completion_tokens') or 0)
        total_tokens = int(self.usage.get('total_tokens') or 0)
        return {
            'input_tokens': prompt_tokens,
            'output_tokens': completion_tokens,
            'total_tokens': total_tokens,
        }

    def _finish_response(self, status: str = 'completed') -> List[str]:
        if self.completed:
            return []

        self.completed = True
        return [_sse_event('response.completed', {
            'response': {
                'id': self.resp_id,
                'object': 'response',
                'created_at': self.created,
                'status': status,
                'output': self._build_output(),
                'usage': self._build_usage(),
            }
        })]

    def _finish_output_items(self) -> List[str]:
        events: List[str] = []

        if not self.output_item_done:
            self.output_item_done = True
            events.extend(self._finish_text_events())
            if self.output_item_added:
                events.append(_sse_event('response.output_item.done', {
                    'output_index': 0,
                    'item': {
                        'type': 'message',
                        'id': self.msg_id,
                        'status': 'completed',
                        'role': self.message_role,
                        'content': [
                            {
                                'type': 'output_text',
                                'text': self.full_text,
                                'annotations': [],
                            }
                        ] if self.content_part_added else [],
                    }
                }))

        events.extend(self._finish_tool_events())
        return events

    def _process_chunk(self, data: Dict[str, Any]) -> List[str]:
        """处理单个 Chat Completions chunk，生成对应的 Response API 事件"""
        events: List[str] = []

        events.extend(self._ensure_initialized(data))

        usage = data.get('usage')
        if isinstance(usage, dict) and usage:
            self.usage = usage

        choices = data.get('choices', [])
        if not choices:
            return events

        choice = choices[0]
        if not isinstance(choice, dict):
            return events

        delta = choice.get('delta', {}) or {}
        finish_reason = choice.get('finish_reason')

        if delta.get('role'):
            self.message_role = delta['role']

        content = delta.get('content')
        if content:
            events.extend(self._ensure_content_part())
            self.full_text += content
            events.append(_sse_event('response.output_text.delta', {
                'item_id': self.msg_id,
                'output_index': 0,
                'content_index': 0,
                'delta': content,
            }))

        tcs = delta.get('tool_calls')
        if tcs:
            for tc in tcs:
                if isinstance(tc, dict):
                    events.extend(self._process_tool_call_delta(tc))

        if finish_reason is not None and not self.output_item_done:
            status = 'completed'
            if finish_reason in ('length', 'content_filter'):
                status = 'incomplete'
            events.extend(self._finish_output_items())
            events.extend(self._finish_response(status))

        return events

    def finish(self) -> List[str]:
        """外部调用：强制结束流式转换。"""
        return self._finish()

    def _finish(self) -> List[str]:
        events: List[str] = []
        events.extend(self._finish_output_items())
        events.extend(self._finish_response())
        return events


def _convert_id(chat_id: str) -> str:
    """将 chatcmpl-xxx 转换为 resp-xxx"""
    if chat_id.startswith('chatcmpl-'):
        return chat_id.replace('chatcmpl-', 'resp-', 1)
    if chat_id.startswith('chatcmpl'):
        return chat_id.replace('chatcmpl', 'resp', 1)
    return f'resp_{chat_id}' if chat_id else 'resp_unknown'


def _build_response_stub(resp_id: str, created: int, status: str, model: str) -> Dict[str, Any]:
    """构建 Response API 的 response 对象骨架"""
    return {
        'id': resp_id,
        'object': 'response',
        'created_at': created,
        'status': status,
        'error': None,
        'incomplete_details': None,
        'instructions': None,
        'max_output_tokens': None,
        'model': model,
        'output': [],
        'parallel_tool_calls': True,
        'temperature': 1.0,
        'tool_choice': 'auto',
        'tools': [],
        'top_p': 1.0,
        'truncation': 'disabled',
        'usage': {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0,
        },
        'user': None,
        'metadata': {},
    }


def _sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """构造 Response API 格式的 SSE 事件行。"""
    event = {'type': event_type}
    event.update(data)
    return f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
