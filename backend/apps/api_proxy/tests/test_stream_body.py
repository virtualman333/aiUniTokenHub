# -*- coding: utf-8 -*-
"""流式请求体：必须主动向上游索取 usage（纯 Python，不依赖 Django settings 与数据库）

为什么单独立一个文件
--------------------
这件事丢了的表现是「**平台不收钱**」，而代码、日志、界面三处都不报错：

  OpenAI 兼容协议里，流式响应默认**一个 chunk 都不带 `usage`**，要拿到它必须在
  请求里带 `stream_options.include_usage = true`。本仓库此前从没发过这个字段，
  计费就全押在「上游顺手带了 usage」上 —— 上游照规范不带时，收尾那句
  `if total_tokens > 0` 整段跳过扣费：余额不动、`UsageLog` 三个 token 字段全 0、
  账单里没有这一笔，和「这次调用真的免费」完全一样。

  能自动发现的只有断言，所以这里把两件事钉住：

  1. **行为**：`build_stream_body` 对 OpenAI 协议一定带上
     `stream_options.include_usage`，且不因此改动调用方的请求体；
  2. **结构**：两条流式端点都只能通过它拼请求体 —— 谁再自己写一份
     `body['stream'] = True`，测试立刻红。

判定写法说明：结构那几条走 `ast`，不走正则。注释与 docstring 里引用旧写法
会骗过字符串断言（本仓库为此误报过一次），AST 只看代码。

跑法（在 backend/ 下，不需要数据库）：
    python run_tests.py
"""
import ast
import unittest
from pathlib import Path

from apps.api_proxy.adapters.upstream_body import (
    STREAM_OPTIONS_INCLUDE_USAGE,
    build_stream_body,
)

BACKEND = Path(__file__).resolve().parents[3]
OPENAI_VIEWS = BACKEND / 'apps' / 'api_proxy' / 'views_openai.py'
RESPONSES_VIEWS = BACKEND / 'apps' / 'api_proxy' / 'views_responses.py'


def _read(path: Path) -> str:
    assert path.exists(), f'读不到 {path} —— 文件被挪走了？这条锁需要跟着改'
    return path.read_text(encoding='utf-8')


def _called_names(src: str):
    """源码里出现过的调用名（`f(` / `obj.f(`）。走 AST，注释与 docstring 骗不过它。"""
    return [
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(ast.parse(src))
        if isinstance(node, ast.Call)
    ]


def _assign_keys(src: str, var: str):
    """`<var>['键'] = ...` 里的键。用来确认「没人再自己拼请求体」。"""
    keys = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == var
                and isinstance(target.slice, ast.Constant)
            ):
                keys.append(target.slice.value)
    return keys


class BuildStreamBodyTest(unittest.TestCase):
    """客户端请求体 → 上游流式请求体"""

    def test_OpenAI协议必须带上include_usage(self):
        """核心：不主动要，上游就不给 —— 给了才能计费。"""
        body = build_stream_body({'model': 'gpt-4o', 'messages': []})
        self.assertTrue(body['stream'])
        self.assertEqual(
            body['stream_options'].get(STREAM_OPTIONS_INCLUDE_USAGE), True,
            '流式请求没有向上游索取 usage —— 上游按规范不带 usage 时这次就不计费了',
        )

    def test_客户端没传stream_options时自动补上(self):
        body = build_stream_body({'model': 'm'})
        self.assertEqual(body['stream_options'], {'include_usage': True})

    def test_客户端传了null不能把强制项吃掉(self):
        """有的客户端会发 `"stream_options": null` —— 那不等于「不要 usage」。"""
        body = build_stream_body({'model': 'm', 'stream_options': None})
        self.assertEqual(body['stream_options'].get(STREAM_OPTIONS_INCLUDE_USAGE), True)
        # 非 dict 的脏值同理，不能让 `in` 之类炸在请求路径上
        body = build_stream_body({'model': 'm', 'stream_options': 'whatever'})
        self.assertEqual(body['stream_options'].get(STREAM_OPTIONS_INCLUDE_USAGE), True)

    def test_客户端传的其它stream_options键保留(self):
        body = build_stream_body({
            'model': 'm',
            'stream_options': {'continuous_usage_stats': True},
        })
        self.assertEqual(body['stream_options']['continuous_usage_stats'], True)
        self.assertEqual(body['stream_options'][STREAM_OPTIONS_INCLUDE_USAGE], True)

    def test_客户端显式关掉include_usage也照样打开(self):
        """计费不能由调用方写一个可选参数关掉。"""
        body = build_stream_body({'model': 'm', 'stream_options': {'include_usage': False}})
        self.assertEqual(body['stream_options'][STREAM_OPTIONS_INCLUDE_USAGE], True)

    def test_不修改入参(self):
        """调用方还要拿原始请求体写 APIAccessLog（不能多出 include_usage）。"""
        original = {'model': 'm', 'stream_options': {'continuous_usage_stats': True}}
        snapshot = {'model': 'm', 'stream_options': {'continuous_usage_stats': True}}

        build_stream_body(original)

        self.assertEqual(original, snapshot, '请求体被就地改了 —— 访问日志会记下代理自己加的字段')
        self.assertNotIn('stream', original)
        self.assertNotIn(STREAM_OPTIONS_INCLUDE_USAGE, original['stream_options'])

    def test_Anthropic协议不加stream_options但一定带stream(self):
        """Anthropic 的流自带 usage，而且它不认 stream_options（塞进去就是 400）。"""
        body = build_stream_body(
            {'model': 'claude-x', 'messages': [{'role': 'user', 'content': 'hi'}]},
            protocol='anthropic',
            model='claude-x',
        )
        self.assertTrue(body['stream'])
        self.assertNotIn('stream_options', body)
        self.assertEqual(body['model'], 'claude-x')
        self.assertEqual(body['messages'][0]['role'], 'user')

    def test_Anthropic协议用传入的model而不是请求体里的(self):
        """上游账号绑定的模型名才是发出去的那个（请求体里的可能只是个别名）。"""
        body = build_stream_body(
            {'model': 'alias', 'messages': [{'role': 'user', 'content': 'hi'}]},
            protocol='anthropic',
            model='claude-real',
        )
        self.assertEqual(body['model'], 'claude-real')

    def test_请求体为空或None不抛(self):
        for value in (None, {}):
            with self.subTest(value=value):
                body = build_stream_body(value)
                self.assertTrue(body['stream'])
                self.assertEqual(body['stream_options'][STREAM_OPTIONS_INCLUDE_USAGE], True)

    def test_protocol缺省或None一律按OpenAI算(self):
        for protocol in ('', None, 'openai'):
            with self.subTest(protocol=protocol):
                body = build_stream_body({'model': 'm'}, protocol=protocol)
                self.assertEqual(body['stream_options'][STREAM_OPTIONS_INCLUDE_USAGE], True)


class 两条流式端点共用一个入口(unittest.TestCase):
    """结构锁：请求体只能有一处拼装，判据只能有一处。"""

    def test_两个视图都调用build_stream_body(self):
        for path in (OPENAI_VIEWS, RESPONSES_VIEWS):
            with self.subTest(path=path.name):
                called = _called_names(_read(path))
                self.assertEqual(
                    called.count('build_stream_body'), 1,
                    f'{path.name} 没有（或不止一次）通过 build_stream_body 拼流式请求体 —— '
                    f'另一个入口就会漏掉 include_usage，那条端点静默不计费',
                )

    def test_视图里不许再自己写body的stream字段(self):
        """`body['stream'] = True` 是原来那两份实现的写法，现在只该出现在 upstream_body.py。"""
        for path in (OPENAI_VIEWS, RESPONSES_VIEWS):
            with self.subTest(path=path.name):
                self.assertNotIn(
                    'stream', _assign_keys(_read(path), 'body'),
                    f'{path.name} 又在自己拼流式请求体了 —— 请走 build_stream_body',
                )

    def test_两个视图都调用了未计费告警(self):
        """成功却没收到 usage = 这笔没收钱，必须两边都留得下痕迹。"""
        for path in (OPENAI_VIEWS, RESPONSES_VIEWS):
            with self.subTest(path=path.name):
                called = _called_names(_read(path))
                self.assertEqual(
                    called.count('unbilled_stream_note'), 1,
                    f'{path.name} 没调用 unbilled_stream_note —— 这条端点「成功但没收到 usage」'
                    f'时会一声不响地不收钱',
                )


if __name__ == '__main__':
    unittest.main()
