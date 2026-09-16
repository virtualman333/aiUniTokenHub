# -*- coding: utf-8 -*-
"""
响应 id 映射的一致性锁（纯 Python，不依赖 Django settings 与数据库）

`_convert_id`（`chatcmpl-xxx` → `resp-xxx`）以前在 `response_adapter.py`（非流式）
与 `streaming_adapter.py`（流式）里各写了一份，**逐字相同**。而测试只覆盖了前者
（`test_adapters.ConvertIdTest`），后一份是裸奔的 —— 两份漂移了也没人会发现。

漂移的后果不是显示错误：`id` 是客户端串上下文用的（`response.previous_response_id`），
同一个上游 `chatcmpl-xxx` 在流式与非流式两条路径上算出不同的 `resp-` id，客户端就
对不上号，而且只在「先流式再非流式」这种组合下才现形。

现在两份实现收敛到 `adapters/ids.py`，这里锁两件事：

  1. 两条路径用的是**同一个函数对象**（`assertIs`）—— 谁要是又复制一份回去，立刻红；
  2. 两个模块里都不许再出现本地 `def _convert_id` —— 直接钉住「不许有第二份实现」。

断言 1 在「已经收敛」的前提下是恒真的，但它防的正是**回退**：按当初那种写法
（复制一份进另一个文件）改坏它，这两条会立刻红。这就是它存在的意义。

跑法（在 backend/ 下，不需要数据库）：
    python run_tests.py
"""
import re
import unittest
from pathlib import Path

from apps.api_proxy.adapters import response_adapter, streaming_adapter
from apps.api_proxy.adapters.ids import convert_response_id

ADAPTERS_DIR = Path(__file__).resolve().parents[1] / 'adapters'


class SingleImplementationTest(unittest.TestCase):
    """不许有第二份实现"""

    def test_两条路径用的是同一个函数对象(self):
        self.assertIs(
            response_adapter._convert_id,
            streaming_adapter._convert_id,
            '流式与非流式各自有了自己的 _convert_id —— 两份实现必然漂移，请都从 .ids 导入',
        )

    def test_两个模块里都不许再定义本地副本(self):
        # 必须编译带 re.M 的 pattern：不带 re.M 时 `^` 只匹配整个字符串的开头，
        # 而源码开头是模块 docstring —— 那样这条断言永远为真，等于没有锁。
        local_def = re.compile(r'^def _convert_id', re.M)
        for name in ('response_adapter.py', 'streaming_adapter.py'):
            with self.subTest(module=name):
                src = (ADAPTERS_DIR / name).read_text(encoding='utf-8')
                self.assertNotRegex(
                    src, local_def,
                    f'{name} 里又出现了本地 def _convert_id，请改为 from .ids import',
                )

    def test_ids模块自己确实定义了它(self):
        # 防止「两边都改成 import」之后源头被删、只剩一个空壳引用
        src = (ADAPTERS_DIR / 'ids.py').read_text(encoding='utf-8')
        self.assertRegex(
            src, re.compile(r'^def convert_response_id', re.M),
            'ids.py 里没有真正的实现',
        )


class ConvertResponseIdTest(unittest.TestCase):
    """映射规则本身（含两个旧实现没覆盖到的输入）"""

    def test_chatcmpl带横线_换成resp带横线(self):
        self.assertEqual(convert_response_id('chatcmpl-abc123'), 'resp-abc123')

    def test_chatcmpl不带横线_直接换前缀(self):
        self.assertEqual(convert_response_id('chatcmplabc'), 'respabc')

    def test_只替换第一处_不误伤正文里的同名串(self):
        # replace(..., 1) 的意义：id 里再出现 chatcmpl 不该被一起换掉
        self.assertEqual(
            convert_response_id('chatcmpl-abc-chatcmpl'),
            'resp-abc-chatcmpl',
        )

    def test_其他形态前缀加resp下划线(self):
        self.assertEqual(convert_response_id('other-1'), 'resp_other-1')

    def test_空字符串给确定值而不是空id(self):
        self.assertEqual(convert_response_id(''), 'resp_unknown')

    def test_结果永不为空(self):
        for raw in ('', None, 'x', 'chatcmpl', 'chatcmpl-'):
            with self.subTest(raw=raw):
                self.assertTrue(convert_response_id(raw))

    def test_None不抛异常(self):
        # 上游缺 id 字段时原来是 AttributeError，把一次正常转发打成 500
        self.assertEqual(convert_response_id(None), 'resp_unknown')

    def test_非字符串id不抛异常(self):
        self.assertEqual(convert_response_id(12345), 'resp_12345')

    def test_返回值始终是字符串(self):
        for raw in ('chatcmpl-1', '', None, 7):
            with self.subTest(raw=raw):
                self.assertIsInstance(convert_response_id(raw), str)


if __name__ == '__main__':
    unittest.main()
