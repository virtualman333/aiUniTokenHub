# -*- coding: utf-8 -*-
"""
api_proxy 协议适配层单元测试（纯 Python，不依赖 Django settings 与数据库）

为什么只测这一层
----------------
`apps/api_proxy/adapters/` 是 OpenAI 协议与 Anthropic 协议之间的转换层，是纯函数，
但它同时决定了**计费口径**：转换出的 prompt_tokens / cached_tokens 直接进
`calculate_and_deduct_cost` 算钱。近几次提交里这一层反复出问题：

  - 16f3094  缓存 token 未计入 prompt_tokens（漏计费）
  - 8932316  工具调用消息转换不完整
  - 7f584b7  输出索引计算错误

而本仓库此前没有任何测试文件，改错了只能等用户账单对不上才发现。
这里把转换层的口径固化下来：尤其 `anthropic_to_openai` 必须把
cache_creation_input_tokens / cache_read_input_tokens 一并计入 prompt_tokens，
一旦有人改回只算 input_tokens，测试立刻红灯。

跑法（在 backend/ 下，不需要数据库）：
    python -m unittest discover -s apps/api_proxy/tests -t . -v
"""
import unittest

from apps.api_proxy.adapters.response_adapter import (
    _convert_id,
    _convert_tool_call,
    _convert_usage,
    _map_finish_reason,
    anthropic_to_openai,
    convert_response,
    map_anthropic_stop_reason,
)


class ConvertUsageTest(unittest.TestCase):
    """Chat Completions usage → Response API usage（计费用口径）"""

    def test_标准用法字段直通(self):
        got = _convert_usage({'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15})
        self.assertEqual(got['input_tokens'], 10)
        self.assertEqual(got['output_tokens'], 5)
        self.assertEqual(got['total_tokens'], 15)

    def test_缺字段一律归零不抛异常(self):
        got = _convert_usage({})
        self.assertEqual(got['input_tokens'], 0)
        self.assertEqual(got['output_tokens'], 0)
        self.assertEqual(got['total_tokens'], 0)
        self.assertEqual(got['input_tokens_details']['cached_tokens'], 0)
        self.assertEqual(got['output_tokens_details']['reasoning_tokens'], 0)

    def test_字段为_None_时归零(self):
        got = _convert_usage({'prompt_tokens': None, 'completion_tokens': None, 'total_tokens': None})
        self.assertEqual(got['input_tokens'], 0)

    def test_缓存命中走_OpenAI_既有的_details_字段(self):
        got = _convert_usage({
            'prompt_tokens': 100,
            'completion_tokens': 10,
            'total_tokens': 110,
            'prompt_tokens_details': {'cached_tokens': 64},
        })
        self.assertEqual(got['input_tokens_details']['cached_tokens'], 64)

    def test_缓存命中回落到_Anthropic_字段(self):
        """上游回的是 Anthropic 原始 usage（没有 prompt_tokens_details）时不能漏掉缓存。"""
        got = _convert_usage({'prompt_tokens': 100, 'cache_read_input_tokens': 64})
        self.assertEqual(got['input_tokens_details']['cached_tokens'], 64)

    def test_details_有值时优先于回落字段(self):
        got = _convert_usage({
            'prompt_tokens': 100,
            'prompt_tokens_details': {'cached_tokens': 32},
            'cache_read_input_tokens': 64,
        })
        self.assertEqual(got['input_tokens_details']['cached_tokens'], 32)

    def test_推理_token_透出(self):
        got = _convert_usage({
            'prompt_tokens': 1, 'completion_tokens': 2, 'total_tokens': 3,
            'completion_tokens_details': {'reasoning_tokens': 7},
        })
        self.assertEqual(got['output_tokens_details']['reasoning_tokens'], 7)

    def test_details_不是字典时不炸(self):
        got = _convert_usage({
            'prompt_tokens': 1,
            'prompt_tokens_details': 'oops',
            'completion_tokens_details': [1, 2],
        })
        self.assertEqual(got['input_tokens_details']['cached_tokens'], 0)
        self.assertEqual(got['output_tokens_details']['reasoning_tokens'], 0)


class AnthropicToOpenAITest(unittest.TestCase):
    """Anthropic 响应 → Chat Completions 响应"""

    @staticmethod
    def _resp(**over):
        resp = {
            'id': 'msg_abc',
            'model': 'claude-x',
            'stop_reason': 'end_turn',
            'content': [{'type': 'text', 'text': '你好'}],
            'usage': {'input_tokens': 100, 'output_tokens': 20},
        }
        resp.update(over)
        return resp

    def test_缓存token必须计入prompt_tokens(self):
        """16f3094 的回归保护：只算 input_tokens 会漏计费。"""
        out = anthropic_to_openai(self._resp(usage={
            'input_tokens': 100,
            'output_tokens': 20,
            'cache_creation_input_tokens': 30,
            'cache_read_input_tokens': 40,
        }))
        usage = out['usage']
        self.assertEqual(usage['prompt_tokens'], 170, '100 + 30(写缓存) + 40(读缓存)')
        self.assertEqual(usage['completion_tokens'], 20)
        self.assertEqual(usage['total_tokens'], 190)
        self.assertEqual(usage['prompt_tokens_details']['cached_tokens'], 40,
                         'cached_tokens 只报读缓存，供折扣价计算')

    def test_无缓存字段时与_input_tokens_相等(self):
        out = anthropic_to_openai(self._resp())
        self.assertEqual(out['usage']['prompt_tokens'], 100)

    def test_转出的_usage_再过一次_convert_usage_口径不丢(self):
        """代理链路里会先 anthropic_to_openai 再 convert_response，两跳后计费口径必须一致。"""
        out = anthropic_to_openai(self._resp(usage={
            'input_tokens': 100, 'output_tokens': 20,
            'cache_creation_input_tokens': 30, 'cache_read_input_tokens': 40,
        }))
        final = _convert_usage(out['usage'])
        self.assertEqual(final['input_tokens'], 170)
        self.assertEqual(final['output_tokens'], 20)
        self.assertEqual(final['total_tokens'], 190)
        self.assertEqual(final['input_tokens_details']['cached_tokens'], 40)

    def test_多个文本块按顺序拼接(self):
        out = anthropic_to_openai(self._resp(content=[
            {'type': 'text', 'text': 'A'},
            {'type': 'text', 'text': 'B'},
        ]))
        self.assertEqual(out['choices'][0]['message']['content'], 'AB')

    def test_tool_use_块转成_tool_calls(self):
        out = anthropic_to_openai(self._resp(content=[
            {'type': 'text', 'text': '调用中'},
            {'type': 'tool_use', 'id': 'toolu_1', 'name': 'get_weather',
             'input': {'city': '深圳'}},
        ]))
        calls = out['choices'][0]['message']['tool_calls']
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['id'], 'toolu_1')
        self.assertEqual(calls[0]['type'], 'function')
        self.assertEqual(calls[0]['function']['name'], 'get_weather')
        self.assertIn('深圳', calls[0]['function']['arguments'])

    def test_纯文本时不带_tool_calls_键(self):
        out = anthropic_to_openai(self._resp())
        self.assertNotIn('tool_calls', out['choices'][0]['message'])

    def test_tool_use_的_input_为空时给空对象(self):
        out = anthropic_to_openai(self._resp(content=[
            {'type': 'tool_use', 'id': 't', 'name': 'f'},
        ]))
        self.assertEqual(out['choices'][0]['message']['tool_calls'][0]['function']['arguments'], '{}')

    def test_非字典内容块被跳过(self):
        out = anthropic_to_openai(self._resp(content=['裸字符串', {'type': 'text', 'text': 'ok'}]))
        self.assertEqual(out['choices'][0]['message']['content'], 'ok')

    def test_stop_reason_映射到_finish_reason(self):
        for src, want in [('end_turn', 'stop'), ('max_tokens', 'length'),
                          ('tool_use', 'tool_calls'), (None, None)]:
            with self.subTest(src=src):
                out = anthropic_to_openai(self._resp(stop_reason=src))
                self.assertEqual(out['choices'][0]['finish_reason'], want)

    def test_无_usage_时不炸(self):
        out = anthropic_to_openai(self._resp(usage=None))
        self.assertEqual(out['usage']['prompt_tokens'], 0)

    def test_响应外层形状(self):
        out = anthropic_to_openai(self._resp())
        self.assertEqual(out['object'], 'chat.completion')
        self.assertEqual(out['id'], 'msg_abc')
        self.assertEqual(out['model'], 'claude-x')
        self.assertIsInstance(out['created'], int)
        self.assertEqual(out['choices'][0]['index'], 0)


class MapAnthropicStopReasonTest(unittest.TestCase):
    def test_四种已知映射(self):
        self.assertEqual(map_anthropic_stop_reason('end_turn'), 'stop')
        self.assertEqual(map_anthropic_stop_reason('max_tokens'), 'length')
        self.assertEqual(map_anthropic_stop_reason('stop_sequence'), 'stop')
        self.assertEqual(map_anthropic_stop_reason('tool_use'), 'tool_calls')

    def test_未知与_None_返回_None(self):
        self.assertIsNone(map_anthropic_stop_reason('pause_turn'))
        self.assertIsNone(map_anthropic_stop_reason(None))


class ConvertIdTest(unittest.TestCase):
    def test_标准前缀替换(self):
        self.assertEqual(_convert_id('chatcmpl-abc123'), 'resp-abc123')

    def test_无短横线前缀替换(self):
        self.assertEqual(_convert_id('chatcmplabc'), 'respabc')

    def test_其他前缀加_下划线(self):
        self.assertEqual(_convert_id('other-1'), 'resp_other-1')

    def test_空值给兜底(self):
        self.assertEqual(_convert_id(''), 'resp_unknown')


class MapFinishReasonTest(unittest.TestCase):
    def test_正常结束(self):
        self.assertEqual(_map_finish_reason('stop'), ('completed', None))
        self.assertEqual(_map_finish_reason('tool_calls'), ('completed', None))

    def test_长度截断(self):
        self.assertEqual(_map_finish_reason('length'),
                         ('incomplete', {'reason': 'max_output_tokens'}))

    def test_内容过滤(self):
        self.assertEqual(_map_finish_reason('content_filter'),
                         ('incomplete', {'reason': 'content_filter'}))

    def test_尚未结束(self):
        self.assertEqual(_map_finish_reason(None), ('in_progress', None))

    def test_未知值保守判为完成(self):
        self.assertEqual(_map_finish_reason('weird'), ('completed', None))


class ConvertToolCallTest(unittest.TestCase):
    def test_字段重命名与状态补齐(self):
        got = _convert_tool_call({
            'id': 'call_1',
            'type': 'function',
            'function': {'name': 'f', 'arguments': '{"a":1}'},
        })
        self.assertEqual(got['type'], 'tool_call')
        self.assertEqual(got['call_type'], 'function')
        self.assertEqual(got['status'], 'completed')
        self.assertEqual(got['name'], 'f')
        self.assertEqual(got['arguments'], '{"a":1}')

    def test_缺_function_时给默认值(self):
        got = _convert_tool_call({'id': 'call_1'})
        self.assertEqual(got['name'], '')
        self.assertEqual(got['arguments'], '{}')


class ConvertResponseTest(unittest.TestCase):
    """Chat Completions 响应 → Response API 响应（非流式端到端形状）"""

    @staticmethod
    def _chat(**over):
        chat = {
            'id': 'chatcmpl-xyz',
            'created': 1234,
            'model': 'gpt-x',
            'choices': [{
                'index': 0,
                'message': {'role': 'assistant', 'content': 'hi'},
                'finish_reason': 'stop',
            }],
            'usage': {'prompt_tokens': 5, 'completion_tokens': 2, 'total_tokens': 7},
        }
        chat.update(over)
        return chat

    def test_外层字段与_id_前缀(self):
        out = convert_response(self._chat(), {})
        self.assertEqual(out['id'], 'resp-xyz')
        self.assertEqual(out['object'], 'response')
        self.assertEqual(out['status'], 'completed')
        self.assertIsNone(out['error'])
        self.assertEqual(out['created_at'], 1234)
        self.assertEqual(out['model'], 'gpt-x')
        self.assertEqual(out['truncation'], 'disabled')

    def test_output_里是_output_text_条目(self):
        out = convert_response(self._chat(), {})
        self.assertEqual(len(out['output']), 1)
        item = out['output'][0]
        self.assertEqual(item['type'], 'message')
        self.assertEqual(item['role'], 'assistant')
        self.assertEqual(item['status'], 'completed')
        self.assertEqual(item['content'][0],
                         {'type': 'output_text', 'text': 'hi', 'annotations': []})

    def test_截断时状态为_incomplete(self):
        out = convert_response(self._chat(choices=[{
            'index': 0, 'message': {'role': 'assistant', 'content': 'x'},
            'finish_reason': 'length',
        }]), {})
        self.assertEqual(out['status'], 'incomplete')
        self.assertEqual(out['incomplete_details'], {'reason': 'max_output_tokens'})

    def test_tool_calls_进_output_内容数组(self):
        out = convert_response(self._chat(choices=[{
            'index': 0,
            'message': {'role': 'assistant', 'content': '', 'tool_calls': [{
                'id': 'call_1', 'type': 'function',
                'function': {'name': 'f', 'arguments': '{}'},
            }]},
            'finish_reason': 'tool_calls',
        }]), {})
        types = [c['type'] for c in out['output'][0]['content']]
        self.assertIn('tool_call', types)

    def test_usage_走同一套口径(self):
        out = convert_response(self._chat(), {})
        self.assertEqual(out['usage']['input_tokens'], 5)
        self.assertEqual(out['usage']['output_tokens'], 2)
        self.assertEqual(out['usage']['total_tokens'], 7)

    def test_空_choices_不抛异常(self):
        out = convert_response(self._chat(choices=[]), {})
        self.assertEqual(out['output'], [])
        self.assertEqual(out['status'], 'in_progress')

    def test_原始请求参数回填与默认值(self):
        out = convert_response(self._chat(), {'temperature': 0.2, 'max_output_tokens': 128})
        self.assertEqual(out['temperature'], 0.2)
        self.assertEqual(out['max_output_tokens'], 128)
        self.assertEqual(out['top_p'], 1.0, '未提供时用默认值')
        self.assertEqual(out['tool_choice'], 'auto')
        self.assertIs(out['parallel_tool_calls'], True)
        self.assertEqual(out['tools'], [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
