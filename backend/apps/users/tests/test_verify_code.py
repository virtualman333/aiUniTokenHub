# -*- coding: utf-8 -*-
"""邮箱验证码判定的测试 —— 纯 Python，不 import Django。

为什么值得一套用例
------------------
`register` 与 `reset_password` 都会走这条判定，而它此前只存在于 `register` 函数体里：
本轮补忘记密码时，如果就地再抄一遍，就会出现「注册能过的码、忘记密码过不了」这种
只表现为一句莫名其妙提示的漂移。抽成 `apps/users/verify_code.py` 之后它终于可以被
不连库地钉住 —— 这也让**本轮新增的那个端点**第一次有了可跑的测试（端点本身要 ORM，
判定不用）。

锁的是两样东西：**三句话**（用户可见的产品文案）与**它们的顺序**
（「过期」必须盖过「内容不对」，否则用户不知道该重新获取还是该检查有没有打错）。
"""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

from apps.users.verify_code import (
    EXPIRED,
    MISMATCH,
    NO_PROBLEM,
    NO_RECORD,
    code_problem,
)

USERS = Path(__file__).resolve().parents[1]


def record(code='123456', expired=False):
    """鸭子类型的记录 —— 判定只用 `.is_expired` 与 `.code` 两个属性。"""
    return SimpleNamespace(code=code, is_expired=expired)


class CodeProblemTests(unittest.TestCase):

    def test_没有记录(self):
        self.assertEqual(code_problem(None, '123456'), NO_RECORD)

    def test_已过期(self):
        self.assertEqual(code_problem(record(expired=True), '123456'), EXPIRED)

    def test_内容不对(self):
        self.assertEqual(code_problem(record(), '000000'), MISMATCH)

    def test_通过时返回_None_而不是空串(self):
        self.assertIs(code_problem(record(), '123456'), NO_PROBLEM)
        self.assertIsNone(NO_PROBLEM, '调用方写的是 `if problem:`，通过必须是 None 这个哨兵')

    def test_顺序_过期要盖过内容不对(self):
        """同时过期且内容也不对时，报的必须是「过期」那句 —— 这是顺序唯一的证据。"""
        self.assertEqual(code_problem(record(code='999999', expired=True), '123456'), EXPIRED)

    def test_没有记录要盖过其余一切(self):
        self.assertEqual(code_problem(None, ''), NO_RECORD)

    def test_空码不许通过(self):
        for submitted in ('', None, '  '):
            with self.subTest(submitted=submitted):
                self.assertEqual(code_problem(record(code='123456'), submitted), MISMATCH)

    def test_空记录里的码不许通过(self):
        """记录里的码是空串时，提交空串也不许通过 —— 否则「没发码」等于「码对」。"""
        self.assertEqual(code_problem(record(code=''), ''), MISMATCH)

    def test_三句话只在唯一一处定义(self):
        """源码层反向断言：`views.py` 里不许再出现这三句话的字面量。

        「唯一来源」不能只是句口号 —— 判定抽走了、话留在原地，等于换了个地方继续漂移。
        """
        source = (USERS / 'views.py').read_text(encoding='utf-8')
        offenders = [s for s in (NO_RECORD, EXPIRED, MISMATCH) if s in source]
        self.assertEqual(
            offenders, [],
            f'这三句话又出现在 views.py 里了：{offenders} —— 判定与文案的唯一来源是 verify_code.py',
        )

    def test_两个调用点都走同一个判定(self):
        """`register` 与 `reset_password` 都必须调 `code_problem`，且都不许自己写 `is_expired`。"""
        tree = ast.parse((USERS / 'views.py').read_text(encoding='utf-8'))
        callers, hand_rolled = [], []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id == 'code_problem':
                    callers.append(node.name)
                if isinstance(sub, ast.Attribute) and sub.attr == 'is_expired':
                    hand_rolled.append(node.name)
        self.assertEqual(sorted(set(callers)), ['register', 'reset_password'],
                         f'这两个动作没都走 code_problem：{sorted(set(callers))}')
        self.assertEqual(hand_rolled, [],
                         f'这些动作自己判了 is_expired，绕过了唯一来源：{sorted(set(hand_rolled))}')


if __name__ == '__main__':
    unittest.main()
