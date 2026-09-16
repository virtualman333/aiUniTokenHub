# -*- coding: utf-8 -*-
"""
流式转换层单元测试（纯 Python，不依赖 Django settings 与数据库）

为什么需要这一组
----------------
`apps/api_proxy/adapters/streaming_adapter.py` 里有两条流式链路，它们**逐字节**
处理上游 SSE，是整条转发路径上最容易出错、也最不容易被发现的一层：

  - `StreamingConverter`               Chat Completions SSE → Response API SSE
  - `AnthropicStreamToOpenAIConverter` Anthropic Messages SSE → Chat Completions chunk

上一轮只覆盖了纯函数式的 `response_adapter` / `request_adapter`，这两个**状态机**
一个断言都没有，而近几次线上问题恰好都出在这一带（`8932316` 工具转换不完整、
`7f584b7` 输出索引错误）。本轮补上，并锁住三处实际缺陷：

  1. 多字节 UTF-8 被 chunk 边界切坏 —— 一个汉字变三个 `�`，且不可恢复
     （`views_openai` / `views_responses` 的 usage 解析缓冲同源，故一并修）
  2. 工具调用先于正文时，`response.completed.output` 的数组顺序与已公布的
     `output_index` 对不上
  3. 标准流（带 finish_reason 的 chunk + 随后的 `[DONE]`）下，工具调用的收尾事件
     被重复发两遍

跑法（在 backend/ 下，不需要数据库）：
    python -m unittest discover -s apps/api_proxy/tests -t . -v
"""
import json
import unittest
from typing import Any, Dict, List, Optional

from apps.api_proxy.adapters.streaming_adapter import (
    AnthropicStreamToOpenAIConverter,
    IncrementalUtf8Decoder,
    StreamingConverter,
)

# ── 构造与解析工具 ────────────────────────────────────────────────────────


def chat_sse(
    delta: Optional[Dict[str, Any]] = None,
    finish_reason: Optional[str] = None,
    usage: Optional[Dict[str, Any]] = None,
    cid: str = 'chatcmpl-1',
    model: str = 'gpt-4o',
) -> bytes:
    """构造一个 Chat Completions 流式 chunk（上游格式）。"""
    body: Dict[str, Any] = {
        'id': cid,
        'object': 'chat.completion.chunk',
        'created': 1_700_000_000,
        'model': model,
        'choices': [{'index': 0, 'delta': delta or {}, 'finish_reason': finish_reason}],
    }
    if usage is not None:
        body['usage'] = usage
    return ('data: ' + json.dumps(body, ensure_ascii=False) + '\n\n').encode('utf-8')


def anthropic_sse(event: str, data: Dict[str, Any]) -> bytes:
    """构造一个 Anthropic Messages 流式事件（上游格式）。"""
    return (
        f'event: {event}\ndata: ' + json.dumps(data, ensure_ascii=False) + '\n\n'
    ).encode('utf-8')


def parse_events(lines: List[str]) -> List[Dict[str, Any]]:
    """把转换器输出的 SSE 文本行解析成事件 dict 列表。"""
    out: List[Dict[str, Any]] = []
    for block in lines:
        for line in block.splitlines():
            if not line.startswith('data:'):
                continue
            payload = line[5:].strip()
            if not payload or payload == '[DONE]':
                continue
            out.append(json.loads(payload))
    return out


def event_types(lines: List[str]) -> List[str]:
    return [e['type'] for e in parse_events(lines)]


def count_type(lines: List[str], event_type: str) -> int:
    return event_types(lines).count(event_type)


def split_in_middle_of(payload: bytes, text: str) -> tuple:
    """把一个多字节字符切成两半，模拟落在字符中间的网络分片。"""
    raw = text.encode('utf-8')
    pos = payload.index(raw)
    cut = pos + 1  # 切在该字符的第 1 个字节之后
    return payload[:cut], payload[cut:]


# ── 增量解码器 ────────────────────────────────────────────────────────────


class IncrementalUtf8DecoderTest(unittest.TestCase):
    def test_三字节汉字跨_chunk_完整还原(self):
        d = IncrementalUtf8Decoder()
        raw = '你'.encode('utf-8')
        self.assertEqual(d.decode(raw[:1]), '')
        self.assertEqual(d.decode(raw[1:]), '你')

    def test_四字节_emoji_跨_chunk_完整还原(self):
        d = IncrementalUtf8Decoder()
        raw = '🙂'.encode('utf-8')
        self.assertEqual(d.decode(raw[:2]), '')
        self.assertEqual(d.decode(raw[2:]), '🙂')

    def test_连续多次切分不产生替换字符(self):
        d = IncrementalUtf8Decoder()
        out = ''
        for b in '你好世界'.encode('utf-8'):
            out += d.decode(bytes([b]))
        self.assertEqual(out, '你好世界')
        self.assertNotIn('\ufffd', out)

    def test_对比单次_decode_的错误行为(self):
        """把「为什么不能直接 decode」写成断言，避免有人改回去。"""
        raw = '你'.encode('utf-8')
        self.assertEqual(raw[:1].decode('utf-8', errors='replace'), '\ufffd')
        d = IncrementalUtf8Decoder()
        d.decode(raw[:1])
        self.assertEqual(d.decode(raw[1:]), '你')

    def test_flush_吐出残留(self):
        d = IncrementalUtf8Decoder()
        d.decode(b'\xe4\xbd')  # 不完整序列，永远补不齐
        self.assertEqual(d.flush(), '\ufffd')

    def test_纯_ascii_不受影响(self):
        d = IncrementalUtf8Decoder()
        self.assertEqual(d.decode(b'hello '), 'hello ')
        self.assertEqual(d.decode(b'world'), 'world')


# ── Chat Completions → Response API ──────────────────────────────────────


class StreamingConverterDecodeTest(unittest.TestCase):
    def test_中文内容跨_chunk_不产生替换字符(self):
        payload = chat_sse(delta={'content': '你好世界'})
        a, b = split_in_middle_of(payload, '好')
        c = StreamingConverter()
        c.feed(a)
        out = c.feed(b)
        self.assertEqual(c.full_text, '你好世界')
        self.assertNotIn('\ufffd', ''.join(out))

    def test_跨_chunk_的_delta_事件里文本也完整(self):
        payload = chat_sse(delta={'content': '中文测试'})
        a, b = split_in_middle_of(payload, '测')
        c = StreamingConverter()
        c.feed(a)
        deltas = [
            e['delta'] for e in parse_events(c.feed(b)) if e['type'] == 'response.output_text.delta'
        ]
        self.assertEqual(deltas, ['中文测试'])

    def test_事件被切成两半时先暂存再产出(self):
        whole = chat_sse(delta={'content': 'x'})
        c = StreamingConverter()
        # 在任何一半里都还没出现 \n\n 时，不能产出事件
        head, tail = whole[:20], whole[20:]
        self.assertEqual(c.feed(head), [])
        # 补齐终止符后才一次性产出该 chunk 对应的全部事件
        self.assertEqual(
            event_types(c.feed(tail)),
            [
                'response.created',
                'response.in_progress',
                'response.output_item.added',
                'response.content_part.added',
                'response.output_text.delta',
            ],
        )
        self.assertEqual(c.full_text, 'x')

    def test_兼容_crlf_分隔(self):
        body = json.dumps(
            {
                'id': 'chatcmpl-1',
                'model': 'gpt-4o',
                'created': 1,
                'choices': [{'delta': {'content': 'a'}, 'finish_reason': None}],
            }
        )
        c = StreamingConverter()
        events = c.feed(('data: ' + body + '\r\n\r\n').encode('utf-8'))
        self.assertIn('response.output_text.delta', event_types(events))

    def test_非_json_的_data_行被跳过且不影响后续(self):
        c = StreamingConverter()
        events = c.feed(b'data: {broken\n\n')
        self.assertEqual(events, [])
        events = c.feed(chat_sse(delta={'content': 'ok'}))
        self.assertEqual(c.full_text, 'ok')

    def test_多个_data_行按_sse_规范拼接(self):
        payload = '{"id":"chatcmpl-1","model":"m","created":1,\n"choices":[{"delta":{"content":"y"},"finish_reason":null}]}'
        c = StreamingConverter()
        c.feed(('data: ' + payload.replace('\n', '\ndata: ') + '\n\n').encode('utf-8'))
        self.assertEqual(c.full_text, 'y')


class StreamingConverterStateMachineTest(unittest.TestCase):
    def test_首个_chunk_只发一次_created_与_in_progress(self):
        c = StreamingConverter()
        first = c.feed(chat_sse(delta={'role': 'assistant'}))
        self.assertEqual(event_types(first), ['response.created', 'response.in_progress'])
        second = c.feed(chat_sse(delta={'content': 'a'}))
        self.assertEqual(count_type(second, 'response.created'), 0)
        self.assertEqual(count_type(second, 'response.in_progress'), 0)

    def test_文本流完整事件序列(self):
        c = StreamingConverter()
        events: List[str] = []
        events += c.feed(chat_sse(delta={'role': 'assistant'}))
        events += c.feed(chat_sse(delta={'content': '你'}))
        events += c.feed(chat_sse(delta={'content': '好'}))
        events += c.feed(b'data: [DONE]\n\n')
        self.assertEqual(
            event_types(events),
            [
                'response.created',
                'response.in_progress',
                'response.output_item.added',
                'response.content_part.added',
                'response.output_text.delta',
                'response.output_text.delta',
                'response.output_text.done',
                'response.content_part.done',
                'response.output_item.done',
                'response.completed',
            ],
        )

    def test_content_part_在第一个正文前才补齐(self):
        c = StreamingConverter()
        c.feed(chat_sse(delta={'role': 'assistant'}))
        self.assertFalse(c.content_part_added)
        c.feed(chat_sse(delta={'content': 'a'}))
        self.assertTrue(c.content_part_added)

    def test_finish_reason_为_length_时状态为_incomplete(self):
        c = StreamingConverter()
        c.feed(chat_sse(delta={'content': 'a'}))
        events = c.feed(chat_sse(finish_reason='length'))
        completed = [e for e in parse_events(events) if e['type'] == 'response.completed'][0]
        self.assertEqual(completed['response']['status'], 'incomplete')

    def test_正常结束状态为_completed(self):
        c = StreamingConverter()
        c.feed(chat_sse(delta={'content': 'a'}))
        events = c.feed(chat_sse(finish_reason='stop'))
        completed = [e for e in parse_events(events) if e['type'] == 'response.completed']
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]['response']['status'], 'completed')
        # 收尾事件必须排在 response.completed 之前
        self.assertLess(
            event_types(events).index('response.output_item.done'),
            event_types(events).index('response.completed'),
        )

    def test_finish_reason_之后再收到_DONE_不重复发收尾事件(self):
        """回归锁：标准流就是「带 finish_reason 的 chunk」+「[DONE]」，两者都会触发收尾。"""
        c = StreamingConverter()
        out: List[str] = []
        out += c.feed(chat_sse(delta={'content': 'a'}))
        out += c.feed(chat_sse(finish_reason='stop'))
        out += c.feed(b'data: [DONE]\n\n')
        for t in (
            'response.output_text.done',
            'response.content_part.done',
            'response.output_item.done',
            'response.completed',
        ):
            self.assertEqual(count_type(out, t), 1, f'{t} 应恰好一次')

    def test_工具调用收尾事件不重复(self):
        c = StreamingConverter()
        out: List[str] = []
        out += c.feed(chat_sse(delta={'tool_calls': [{'index': 0, 'id': 'call_a', 'function': {'name': 'f', 'arguments': '{'}}]}))
        out += c.feed(chat_sse(finish_reason='tool_calls'))
        out += c.feed(b'data: [DONE]\n\n')
        for t in ('response.function_call_arguments.done', 'response.output_item.done'):
            self.assertEqual(count_type(out, t), 1, f'{t} 应恰好一次')

    def test_finish_方法本身幂等(self):
        c = StreamingConverter()
        c.feed(chat_sse(delta={'content': 'a'}))
        self.assertTrue(c.finish())
        self.assertEqual(c.finish(), [])

    def test_工具调用参数分片累积(self):
        c = StreamingConverter()
        events: List[str] = []
        events += c.feed(chat_sse(delta={'tool_calls': [{'index': 0, 'id': 'call_a', 'function': {'name': 'get_weather', 'arguments': '{"ci'}}]}))
        events += c.feed(chat_sse(delta={'tool_calls': [{'index': 0, 'function': {'arguments': 'ty":"SZ"}'}}]}))
        events += c.feed(b'data: [DONE]\n\n')
        self.assertEqual(c.tool_calls[0]['arguments'], '{"city":"SZ"}')
        added = [e for e in parse_events(events) if e['type'] == 'response.output_item.added'][0]
        self.assertEqual(added['item']['type'], 'function_call')
        self.assertEqual(added['item']['name'], 'get_weather')
        # 首条 added 里 arguments 必须为空，参数只走 delta 通道
        self.assertEqual(added['item']['arguments'], '')

    def test_工具调用_item_id_去掉_call_前缀(self):
        c = StreamingConverter()
        c.feed(chat_sse(delta={'tool_calls': [{'index': 0, 'id': 'call_abc', 'function': {'name': 'f', 'arguments': ''}}]}))
        self.assertEqual(c.tool_calls[0]['item_id'], 'fc_abc')

    def test_多个工具调用各自独立索引(self):
        c = StreamingConverter()
        out: List[str] = []
        out += c.feed(chat_sse(delta={'tool_calls': [{'index': 0, 'id': 'call_a', 'function': {'name': 'f0', 'arguments': ''}}]}))
        out += c.feed(chat_sse(delta={'tool_calls': [{'index': 1, 'id': 'call_b', 'function': {'name': 'f1', 'arguments': ''}}]}))
        out += c.feed(b'data: [DONE]\n\n')
        indices = [
            e['output_index']
            for e in parse_events(out)
            if e['type'] == 'response.output_item.added'
        ]
        self.assertEqual(indices, [0, 1])
        self.assertEqual(count_type(out, 'response.output_item.done'), 2)

    def test_纯工具调用时不产生空_message_条目(self):
        c = StreamingConverter()
        c.feed(chat_sse(delta={'tool_calls': [{'index': 0, 'id': 'call_a', 'function': {'name': 'f', 'arguments': '{}'}}]}))
        events = c.feed(b'data: [DONE]\n\n')
        completed = [e for e in parse_events(events) if e['type'] == 'response.completed'][0]
        self.assertEqual([o['type'] for o in completed['response']['output']], ['function_call'])

    def test_无_choices_的_chunk_只做初始化(self):
        c = StreamingConverter()
        payload = json.dumps(
            {'id': 'chatcmpl-1', 'model': 'gpt-4o', 'created': 1, 'usage': {'prompt_tokens': 5}, 'choices': []}
        )
        events = c.feed(('data: ' + payload + '\n\n').encode('utf-8'))
        self.assertEqual(event_types(events), ['response.created', 'response.in_progress'])
        self.assertEqual(c.usage['prompt_tokens'], 5)

    def test_usage_映射到_input_output_total(self):
        c = StreamingConverter()
        c.feed(chat_sse(delta={'content': 'a'}))
        events = c.feed(
            chat_sse(
                finish_reason='stop',
                usage={'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18},
            )
        )
        completed = [e for e in parse_events(events) if e['type'] == 'response.completed'][0]
        self.assertEqual(
            completed['response']['usage'],
            {'input_tokens': 11, 'output_tokens': 7, 'total_tokens': 18},
        )
        # usage 到达后再收 [DONE]，不得重复发收尾事件
        self.assertEqual(c.feed(b'data: [DONE]\n\n'), [])

    def test_id_与响应外层形状(self):
        c = StreamingConverter()
        first = parse_events(c.feed(chat_sse(cid='chatcmpl-xyz', delta={'role': 'assistant'})))
        self.assertEqual(first[0]['response']['id'], 'resp-xyz')
        self.assertEqual(first[0]['response']['object'], 'response')
        self.assertEqual(first[0]['response']['status'], 'in_progress')

    def test_流结束时未收到_finish_reason_也能收尾(self):
        c = StreamingConverter()
        c.feed(chat_sse(delta={'content': 'a'}))
        events = c.feed(b'data: [DONE]\n\n')
        self.assertEqual(count_type(events, 'response.completed'), 1)


class StreamingConverterOutputOrderTest(unittest.TestCase):
    """`response.completed.output` 的顺序必须与已公布的 output_index 一致。"""

    def _announced_indices(self, events: List[str]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for e in parse_events(events):
            if e['type'] == 'response.output_item.added':
                out[e['item']['type']] = e['output_index']
        return out

    def test_工具先于正文时数组顺序仍与_index_一致(self):
        """回归锁：此前固定「先 message 后 tool」，导致 message 公布 index=1 却排在数组第 0 位。"""
        c = StreamingConverter()
        events: List[str] = []
        events += c.feed(chat_sse(delta={'tool_calls': [{'index': 0, 'id': 'call_a', 'function': {'name': 'f', 'arguments': '{}'}}]}))
        events += c.feed(chat_sse(delta={'content': '正文'}))
        events += c.feed(b'data: [DONE]\n\n')

        announced = self._announced_indices(events)
        completed = [e for e in parse_events(events) if e['type'] == 'response.completed'][0]
        order = [o['type'] for o in completed['response']['output']]

        self.assertEqual(announced, {'function_call': 0, 'message': 1})
        self.assertEqual(order, ['function_call', 'message'])
        self.assertEqual(order, sorted(announced, key=lambda t: announced[t]))

    def test_正文先于工具时顺序自然一致(self):
        c = StreamingConverter()
        events: List[str] = []
        events += c.feed(chat_sse(delta={'content': '正文'}))
        events += c.feed(chat_sse(delta={'tool_calls': [{'index': 0, 'id': 'call_a', 'function': {'name': 'f', 'arguments': '{}'}}]}))
        events += c.feed(b'data: [DONE]\n\n')
        announced = self._announced_indices(events)
        completed = [e for e in parse_events(events) if e['type'] == 'response.completed'][0]
        self.assertEqual(announced, {'message': 0, 'function_call': 1})
        self.assertEqual(
            [o['type'] for o in completed['response']['output']], ['message', 'function_call']
        )

    def test_收尾事件也按_output_index_顺序(self):
        c = StreamingConverter()
        events: List[str] = []
        events += c.feed(chat_sse(delta={'tool_calls': [{'index': 0, 'id': 'call_a', 'function': {'name': 'f', 'arguments': '{}'}}]}))
        events += c.feed(chat_sse(delta={'content': '正文'}))
        events += c.feed(b'data: [DONE]\n\n')
        done_indices = [
            e['output_index']
            for e in parse_events(events)
            if e['type'] == 'response.output_item.done'
        ]
        self.assertEqual(done_indices, [0, 1])


# ── Anthropic → Chat Completions ─────────────────────────────────────────


class AnthropicConverterDecodeTest(unittest.TestCase):
    def test_中文增量跨_chunk_不产生替换字符(self):
        payload = anthropic_sse(
            'content_block_delta',
            {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': '你好'}},
        )
        a, b = split_in_middle_of(payload, '好')
        c = AnthropicStreamToOpenAIConverter('claude-x')
        c.feed(a)
        events = parse_events(c.feed(b))
        self.assertEqual([e['choices'][0]['delta'] for e in events], [{'content': '你好'}])

    def test_四个字节的_emoji_跨_chunk(self):
        payload = anthropic_sse(
            'content_block_delta',
            {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': '🙂好'}},
        )
        raw = '🙂好'.encode('utf-8')
        pos = payload.index(raw)
        c = AnthropicStreamToOpenAIConverter('claude-x')
        c.feed(payload[: pos + 3])  # emoji 的 4 字节切在最后一字节前
        events = parse_events(c.feed(payload[pos + 3:]))
        self.assertEqual(events[0]['choices'][0]['delta']['content'], '🙂好')


class AnthropicConverterStateMachineTest(unittest.TestCase):
    def test_message_start_产出_role_chunk_并累计_usage(self):
        c = AnthropicStreamToOpenAIConverter('claude-x')
        events = parse_events(
            c.feed(
                anthropic_sse(
                    'message_start',
                    {
                        'type': 'message_start',
                        'message': {
                            'id': 'msg_1',
                            'model': 'claude-x',
                            'usage': {
                                'input_tokens': 100,
                                'output_tokens': 0,
                                'cache_creation_input_tokens': 20,
                                'cache_read_input_tokens': 30,
                            },
                        },
                    },
                )
            )
        )
        self.assertEqual(events[0]['choices'][0]['delta'], {'role': 'assistant'})
        self.assertEqual(events[0]['id'], 'msg_1')
        # 缓存 token 必须计入 prompt_tokens，否则缓存命中漏计费
        self.assertEqual(c.usage['prompt_tokens'], 150)
        self.assertEqual(c.usage['prompt_tokens_details'], {'cached_tokens': 30})

    def test_message_delta_回填_usage_与_finish_reason(self):
        c = AnthropicStreamToOpenAIConverter('claude-x')
        c.feed(anthropic_sse('message_start', {'type': 'message_start', 'message': {'id': 'msg_1'}}))
        events = parse_events(
            c.feed(
                anthropic_sse(
                    'message_delta',
                    {'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}, 'usage': {'output_tokens': 42}},
                )
            )
        )
        self.assertEqual(events[0]['choices'][0]['finish_reason'], 'stop')
        self.assertEqual(events[0]['usage']['completion_tokens'], 42)
        self.assertEqual(events[0]['usage']['total_tokens'], 42)

    def test_stop_reason_四种映射(self):
        cases = {
            'end_turn': 'stop',
            'max_tokens': 'length',
            'stop_sequence': 'stop',
            'tool_use': 'tool_calls',
        }
        for anthropic_reason, openai_reason in cases.items():
            c = AnthropicStreamToOpenAIConverter('claude-x')
            c.feed(anthropic_sse('message_start', {'type': 'message_start', 'message': {'id': 'm'}}))
            events = parse_events(
                c.feed(
                    anthropic_sse('message_delta', {'type': 'message_delta', 'delta': {'stop_reason': anthropic_reason}})
                )
            )
            self.assertEqual(events[0]['choices'][0]['finish_reason'], openai_reason)

    def test_tool_use_开始与参数分片(self):
        c = AnthropicStreamToOpenAIConverter('claude-x')
        start = parse_events(
            c.feed(
                anthropic_sse(
                    'content_block_start',
                    {
                        'type': 'content_block_start',
                        'index': 1,
                        'content_block': {'type': 'tool_use', 'id': 'toolu_1', 'name': 'get_weather'},
                    },
                )
            )
        )
        call = start[0]['choices'][0]['delta']['tool_calls'][0]
        self.assertEqual(call['index'], 1)
        self.assertEqual(call['id'], 'toolu_1')
        self.assertEqual(call['function']['name'], 'get_weather')

        first = parse_events(
            c.feed(anthropic_sse('content_block_delta', {'type': 'content_block_delta', 'index': 1, 'delta': {'type': 'input_json_delta', 'partial_json': '{"ci'}}))
        )
        second = parse_events(
            c.feed(anthropic_sse('content_block_delta', {'type': 'content_block_delta', 'index': 1, 'delta': {'type': 'input_json_delta', 'partial_json': 'ty":"SZ"}'}}))
        )
        self.assertEqual(first[0]['choices'][0]['delta']['tool_calls'][0]['function']['arguments'], '{"ci')
        self.assertEqual(second[0]['choices'][0]['delta']['tool_calls'][0]['function']['arguments'], 'ty":"SZ"}')
        self.assertEqual(c.tool_calls[1]['arguments'], '{"city":"SZ"}')

    def test_文本块之外的_content_block_start_不产出事件(self):
        c = AnthropicStreamToOpenAIConverter('claude-x')
        events = c.feed(
            anthropic_sse(
                'content_block_start',
                {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text'}},
            )
        )
        self.assertEqual(events, [])

    def test_message_stop_产出_DONE_且不重复(self):
        c = AnthropicStreamToOpenAIConverter('claude-x')
        events = c.feed(anthropic_sse('message_stop', {'type': 'message_stop'}))
        self.assertEqual(events, ['data: [DONE]\n\n'])
        self.assertEqual(c.finish(), [])

    def test_finish_在未收到_message_stop_时兜底_DONE(self):
        c = AnthropicStreamToOpenAIConverter('claude-x')
        self.assertEqual(c.finish(), ['data: [DONE]\n\n'])
        self.assertEqual(c.finish(), [])

    def test_未知事件类型被忽略(self):
        c = AnthropicStreamToOpenAIConverter('claude-x')
        self.assertEqual(c.feed(anthropic_sse('ping', {'type': 'ping'})), [])
        self.assertEqual(c.feed(anthropic_sse('content_block_stop', {'type': 'content_block_stop', 'index': 0})), [])

    def test_chunk_外层形状(self):
        c = AnthropicStreamToOpenAIConverter('claude-x')
        c.feed(anthropic_sse('message_start', {'type': 'message_start', 'message': {'id': 'msg_9'}}))
        events = parse_events(c.feed(anthropic_sse('content_block_delta', {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': 'a'}})))
        e = events[0]
        self.assertEqual(e['object'], 'chat.completion.chunk')
        self.assertEqual(e['id'], 'msg_9')
        self.assertEqual(e['choices'][0]['index'], 0)
        self.assertIsNone(e['choices'][0]['finish_reason'])
        self.assertNotIn('usage', e)

    def test_非法_json_事件被跳过(self):
        c = AnthropicStreamToOpenAIConverter('claude-x')
        self.assertEqual(c.feed(b'event: message_start\ndata: {oops\n\n'), [])
        self.assertEqual(c.feed(anthropic_sse('ping', {'type': 'ping'})), [])


if __name__ == '__main__':
    unittest.main()
