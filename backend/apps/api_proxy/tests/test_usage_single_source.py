# -*- coding: utf-8 -*-
"""「用量解析与收尾记账只有一处」的结构锁（纯 Python，不连数据库）。

为什么要有它
------------
「从上游返回体里读出用了多少 token」这件事，第 9 轮之前在后端写了**四份**：

  - `views_openai._update_usage_log`（非流式）
  - `views_responses._update_usage_log`（非流式）
  - `views_openai` 的 `_handle_streaming` 收尾
  - `views_responses._finalize_stream` 收尾

四份的差别不在风格，在**认得的字段**：只有一份认 Responses API 的
`input_tokens`，只有两份认 Anthropic 的 `cache_read_input_tokens`。
后果是同一个上游、同一个请求，换个端点可能算出不同的用量 ——
而用量直接决定收多少钱（缓存命中的 input 按折扣单价计费）。

行为层面的正确性由 `apps/utils/tests/test_billing_usage.py` 真正跑。
这里锁的是**结构**：那四份不许再长回来。

跑法（在 backend/ 下）：python run_tests.py
"""
import ast
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]

OPENAI_VIEWS = BACKEND / 'apps' / 'api_proxy' / 'views_openai.py'
RESPONSES_VIEWS = BACKEND / 'apps' / 'api_proxy' / 'views_responses.py'
UTILS_BILLING = BACKEND / 'apps' / 'utils' / 'billing.py'

#: 解析上游用量时才会出现的字段名。它们只该出现在 `apps/utils/billing.py`。
USAGE_FIELD_NAMES = (
    'prompt_tokens_details',
    'input_tokens_details',
    'cache_read_input_tokens',
)

#: 「只有一处实现」的函数名
SINGLE_SOURCE_FUNCTIONS = (
    'parse_usage_dict',
    'parse_usage',
    'update_usage_log',
    'charge_usage',
    'apply_usage_to_log',
)


def _read(path: Path) -> str:
    assert path.exists(), f'读不到 {path} —— 文件被挪走了？这条锁需要跟着改'
    return path.read_text(encoding='utf-8')


def _string_literals(src: str) -> list:
    """源码里的字符串字面量（注释与 docstring 之外的）。

    为什么必须走 AST：本轮在 views 里留下的注释正好在**解释**这次收敛
    （「以前这里自己写了一份，不认 `input_tokens_details`」）。
    用 `in src` 去断言「文件里不该出现这个字段名」，命中的就是那句说明 ——
    测出一个假结论，而且很难看出来。
    """
    tree = ast.parse(src)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, 'body', None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    return [
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def _called_names(src: str) -> set:
    """被调用的函数名（AST 取；注释、docstring 天然不在其中）。"""
    names = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _defined_names(src: str) -> set:
    """定义了的函数 / 方法名（含方法 —— `def _update_usage_log` 也算）。"""
    names = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


class UsageParsingLivesInOnePlaceTest(unittest.TestCase):

    def test_视图里不许再手写用量字段名(self):
        # 只要有人在视图里重新 `response_data.get('prompt_tokens_details')`，
        # 就等于又开了一份解析 —— 而两份一定会在某个上游形态上分叉。
        for path in (OPENAI_VIEWS, RESPONSES_VIEWS):
            with self.subTest(file=path.name):
                found = [s for s in _string_literals(_read(path)) if s in USAGE_FIELD_NAMES]
                self.assertEqual(
                    found, [],
                    f'{path.name} 里又出现了用量字段名 {found} —— '
                    f'解析只用 apps.utils.billing.parse_usage_dict（曾有四份，各认不同字段）',
                )

    def test_两个端点都必须走共用的收尾实现(self):
        for path in (OPENAI_VIEWS, RESPONSES_VIEWS):
            with self.subTest(file=path.name):
                self.assertIn(
                    'update_usage_log', _called_names(_read(path)),
                    f'{path.name} 没走 views_openai.update_usage_log —— '
                    f'两个端点各写一份收尾，用量与 cached_tokens 迟早再漂移',
                )

    def test_不再有各自那份_update_usage_log(self):
        # 这条锁的是「结构性回退」：把方法重新写回视图里，就又会变成两份。
        for path in (OPENAI_VIEWS, RESPONSES_VIEWS):
            with self.subTest(file=path.name):
                self.assertNotIn(
                    '_update_usage_log', _defined_names(_read(path)),
                    f'{path.name} 里又定义了 _update_usage_log —— '
                    f'收尾记账只有视图外那一处（views_openai.update_usage_log）',
                )

    def test_解析与收尾函数全后端正各有一处定义(self):
        files = sorted(BACKEND.glob('apps/**/*.py'))
        self.assertGreater(len(files), 10, '没扫到几个 .py —— 路径变了？这条锁会形同虚设')
        for name in SINGLE_SOURCE_FUNCTIONS:
            with self.subTest(func=name):
                where = [
                    p.relative_to(BACKEND).as_posix()
                    for p in files if name in _defined_names(_read(p))
                ]
                self.assertEqual(
                    len(where), 1,
                    f'{name} 在 {len(where)} 个文件里都有定义：{where} —— '
                    f'同一件事写两遍必然漂移（本轮刚把四份并成一份）',
                )

    def test_共用的那一份确实在_billing_里(self):
        # 免得「收敛」成把实现挪到某个视图里、另一个视图反过来 import 它 ——
        # 那样解析逻辑仍然挂在端点文件上，边界会慢慢糊掉。
        for name in ('parse_usage_dict', 'parse_usage'):
            with self.subTest(func=name):
                self.assertIn(name, _defined_names(_read(UTILS_BILLING)))

    def test_共用的收尾确实会把用量写进日志(self):
        # `cached_tokens` 曾经只有流式收尾记。非流式漏记的后果是
        # 「钱按缓存折扣收了、用量明细里缓存是 0」，对账时解释不通。
        body = _read(OPENAI_VIEWS)
        tree = ast.parse(body)
        target = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'apply_usage_to_log':
                target = node
        self.assertIsNotNone(target, '找不到 apply_usage_to_log —— 改名了？这条锁需要跟着改')
        assigned = {
            t.attr for sub in ast.walk(target) if isinstance(sub, ast.Assign)
            for t in sub.targets if isinstance(t, ast.Attribute)
        }
        for field in ('input_tokens', 'output_tokens', 'total_tokens', 'cached_tokens'):
            with self.subTest(field=field):
                self.assertIn(
                    field, assigned,
                    f'apply_usage_to_log 不再写 log.{field} —— '
                    f'四个 token 字段必须在同一处落盘，漏一个就是「钱收了、账对不上」',
                )


if __name__ == '__main__':
    unittest.main()
