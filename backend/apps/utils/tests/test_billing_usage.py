# -*- coding: utf-8 -*-
"""`billing.parse_usage_dict` / `parse_usage` 的测试（纯函数，不连数据库）。

锁的是「这笔到底用了多少 token」这件事。它直接决定收多少钱，而缓存命中
（`cached_tokens`）是**打折**的依据 —— 漏读它 = 按全价收，用户看不见、
对账时也对不出来。这层解析原先在三个地方各写一份，认得的字段各不相同：

  - `views_openai._update_usage_log`：只认 OpenAI 形态
  - `views_responses._update_usage_log`：额外认 Responses 形态
  - `views_responses._finalize_stream`：只认 OpenAI + Anthropic 的缓存字段

于是同一个上游、同一个请求，换个端点就可能算出不同的用量。现在并成一处，
这里把三种形态与脏值都钉住。

跑法（在 backend/ 下）：python run_tests.py
"""
import unittest

from apps.utils.billing import TokenUsage, parse_usage, parse_usage_dict


class OpenAiShapeTest(unittest.TestCase):
    """OpenAI / 兼容格式：prompt_tokens / completion_tokens / total_tokens"""

    def test_标准形态(self):
        usage = parse_usage_dict({
            'prompt_tokens': 120, 'completion_tokens': 30, 'total_tokens': 150,
        })
        self.assertEqual(usage, TokenUsage(120, 30, 150, 0))

    def test_缓存命中在_prompt_tokens_details(self):
        usage = parse_usage_dict({
            'prompt_tokens': 1000, 'completion_tokens': 10, 'total_tokens': 1010,
            'prompt_tokens_details': {'cached_tokens': 896},
        })
        self.assertEqual(usage.cached_tokens, 896, '漏读缓存命中就会按全价收费')

    def test_Anthropic_用_cache_read_input_tokens(self):
        # Anthropic 没有 details 那一层，缓存是单独一个字段
        usage = parse_usage_dict({
            'prompt_tokens': 1000, 'completion_tokens': 10, 'total_tokens': 1010,
            'cache_read_input_tokens': 512,
        })
        self.assertEqual(usage.cached_tokens, 512)

    def test_两家缓存字段同时存在时以_details为准(self):
        # 代理会把 Anthropic 的字段顺手补进 OpenAI 形态，两处都有值时不能来回跳
        usage = parse_usage_dict({
            'prompt_tokens': 10, 'completion_tokens': 1, 'total_tokens': 11,
            'prompt_tokens_details': {'cached_tokens': 7},
            'cache_read_input_tokens': 3,
        })
        self.assertEqual(usage.cached_tokens, 7)


class ResponsesShapeTest(unittest.TestCase):
    """Responses API：input_tokens / output_tokens / input_tokens_details"""

    def test_三个字段都映射过来(self):
        usage = parse_usage_dict({
            'input_tokens': 88, 'output_tokens': 12, 'total_tokens': 100,
        })
        self.assertEqual(usage, TokenUsage(88, 12, 100, 0))

    def test_缓存命中在_input_tokens_details(self):
        # 这一条是「少认一种形态」的代价：认不出它，缓存折扣就成了摆设
        usage = parse_usage_dict({
            'input_tokens': 1000, 'output_tokens': 5, 'total_tokens': 1005,
            'input_tokens_details': {'cached_tokens': 640},
        })
        self.assertEqual(usage.cached_tokens, 640)

    def test_input_tokens_为零时仍按_Responses_形态解析(self):
        # 边界：用真值判断（`if raw.get('input_tokens')`）会把这个正经响应
        # 当成 OpenAI 形态 —— 于是 output_tokens 读成 0，这笔疑似没用量、不计费。
        usage = parse_usage_dict({'input_tokens': 0, 'output_tokens': 5, 'total_tokens': 5})
        self.assertEqual(usage.output_tokens, 5, 'input_tokens=0 被误判成「没有这个字段」了')
        self.assertEqual(usage.total_tokens, 5)

    def test_两种形态不会互相误判(self):
        # 字段名没有交集，所以指纹判定是安全的 —— 这条把它钉住
        openai_like = parse_usage_dict({'prompt_tokens': 1, 'completion_tokens': 2, 'total_tokens': 3})
        self.assertEqual(openai_like.input_tokens, 1, 'OpenAI 形态被当成 Responses 形态读了')


class DirtyValueTest(unittest.TestCase):
    """脏值不抛、不放大 —— 一个字段坏掉不该把整条请求打成 500"""

    def test_非字典入参给全零(self):
        for value in (None, 'oops', 42, [], {'usage': None}):
            with self.subTest(value=value):
                self.assertEqual(parse_usage_dict(value), TokenUsage(0, 0, 0, 0))

    def test_字段为_None_给零(self):
        usage = parse_usage_dict({'prompt_tokens': None, 'completion_tokens': None, 'total_tokens': None})
        self.assertEqual(usage, TokenUsage(0, 0, 0, 0))

    def test_数字字符串能转(self):
        usage = parse_usage_dict({'prompt_tokens': '12', 'completion_tokens': '3', 'total_tokens': '15'})
        self.assertEqual(usage, TokenUsage(12, 3, 15, 0))

    def test_乱码不抛且给零(self):
        # 旧实现直接 `int(...)`，这种值会抛出去 —— 而调用方没有 try/except，
        # 于是一个脏字段把整条请求变成 500。
        usage = parse_usage_dict({'prompt_tokens': 'abc', 'completion_tokens': {}, 'total_tokens': 'x'})
        self.assertEqual(usage, TokenUsage(0, 0, 0, 0))

    def test_负数按零处理(self):
        # `-1` 是某些代理表示「用量未知」的约定。真当负数用，会让
        # `if total_tokens > 0` 这类判断出现莫名其妙的行为（比如刚好为 0 时
        # 既不计费也不告警）。
        usage = parse_usage_dict({'prompt_tokens': -1, 'completion_tokens': -2, 'total_tokens': -3})
        self.assertEqual(usage, TokenUsage(0, 0, 0, 0))

    def test_缓存的脏值也不抛(self):
        usage = parse_usage_dict({
            'prompt_tokens': 10, 'completion_tokens': 1, 'total_tokens': 11,
            'prompt_tokens_details': {'cached_tokens': 'n/a'},
        })
        self.assertEqual(usage.cached_tokens, 0)
        self.assertEqual(usage.total_tokens, 11, '一个坏字段不该把整份用量清零')


class ParseUsageWrapperTest(unittest.TestCase):
    """`parse_usage` 走完整返回体：取 `usage` 那层"""

    def test_从返回体里取_usage(self):
        usage = parse_usage({
            'id': 'chatcmpl-1',
            'usage': {'prompt_tokens': 7, 'completion_tokens': 8, 'total_tokens': 15},
            'choices': [{'message': {'content': 'hi'}}],
        })
        self.assertEqual(usage, TokenUsage(7, 8, 15, 0))

    def test_没有_usage_键就是全零(self):
        self.assertEqual(parse_usage({'choices': []}), TokenUsage(0, 0, 0, 0))

    def test_返回体不是字典给全零(self):
        for value in (None, '<html>502 Bad Gateway</html>', 500):
            with self.subTest(value=value):
                self.assertEqual(parse_usage(value), TokenUsage(0, 0, 0, 0))

    def test_两个入口对同一份_usage_给同一结果(self):
        # parse_usage 只是取了外层键，不该有自己的第二套判定
        raw = {
            'prompt_tokens': 33, 'completion_tokens': 4, 'total_tokens': 37,
            'prompt_tokens_details': {'cached_tokens': 20},
        }
        self.assertEqual(parse_usage({'usage': raw}), parse_usage_dict(raw))

    def test_结果可以按下标解包(self):
        # 流式收尾那处是四个变量一起接的，换个顺序就是隐性 bug
        input_tokens, output_tokens, total_tokens, cached = parse_usage_dict({
            'input_tokens': 1, 'output_tokens': 2, 'total_tokens': 3,
            'input_tokens_details': {'cached_tokens': 1},
        })
        self.assertEqual((input_tokens, output_tokens, total_tokens, cached), (1, 2, 3, 1))


if __name__ == '__main__':
    unittest.main()
