# -*- coding: utf-8 -*-
"""`apps/utils/pagination.py` 的用例 —— 分页参数解析、切页、以及「只有一个来源」这件事。

分三块：
  1. 纯逻辑（`parse_page_args` / `slice_page` / `default_page_size_from`）——
     这一块**不碰 Django**，也是这个模块之所以拆出来的理由；
  2. `page_params` 真的去读了 `settings.REST_FRAMEWORK['PAGE_SIZE']` ——
     用一个假的 `django.conf` 顶上去验证，并且带**反向对照**（同一次请求在
     两个 PAGE_SIZE 下必须给出不同的 page_size，否则那个读就是摆设）；
  3. 结构锁 —— 手抄的那 11 处不许长回来、`20` 这个默认值只许有一处、
     说好了要分页的模块要真的在分页（两向对账）。

第 3 块为什么必须存在
--------------------
`settings.py` 里那句 `'PAGE_SIZE': 20` 挂了很久没人读，是因为 DRF 只在配了
`DEFAULT_PAGINATION_CLASS` 时才看它，而本仓一个分页类都没配（每个视图自己手抄）。
「同一份数据写两处」从来不会以「有人改错了」的方式暴露，只会以「两处悄悄不一样」
的方式暴露 —— 所以这里第 1 块锁行为、第 3 块锁来源，缺一块都拦不住。
"""
import ast
import io
import re
import sys
import tokenize
import types
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]

from apps.utils.pagination import (  # noqa: E402  （必须先算出 BACKEND 才能由 run_tests.py 补 sys.path）
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    default_page_size_from,
    page_params,
    parse_page_args,
    slice_page,
)


def strip_comments(text):
    """把源码里的注释换掉，别的原样保留。

    为什么必须剥注释：模块抬头、以及各处解释「以前这里怎么抄的」的注释里，
    本身就写着那行咒语。不剥注释扫，这条锁第一天就红在自己身上 ——
    而那时候人只会去改锁，不会去改代码。用 `tokenize` 而不是按行找 `#`，
    是因为 `'#'` 出现在字符串里时它就不是注释（`get_queryset` 那种地方有）。
    """
    positions = {}
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT:
            positions.setdefault(tok.start[0], tok.start[1])
    lines = []
    for number, line in enumerate(text.splitlines(), start=1):
        if number in positions:
            line = line[:positions[number]]
        lines.append(line)
    return '\n'.join(lines)


def iter_sources():
    """`apps/` 下所有会进产物的 .py（跳过 `tests/` 与 `__pycache__`）。"""
    for path in sorted(BACKEND.glob('apps/**/*.py')):
        rel = path.relative_to(BACKEND).as_posix()
        if '/tests/' in rel or '__pycache__' in rel or rel.endswith('/tests/__init__.py'):
            continue
        yield rel, path.read_text(encoding='utf-8')


class ParsePageArgsTests(unittest.TestCase):
    """把客户端来的字符串翻成 (page, page_size)，**永不抛异常**。"""

    def test_默认值(self):
        self.assertEqual(parse_page_args({}), (1, 20, ''))

    def test_空串与空白算没传(self):
        # `?page=&page_size=` 是客户端在「清空筛选」时最常见的形态，不是错误
        self.assertEqual(parse_page_args({'page': '', 'page_size': ''}), (1, 20, ''))
        self.assertEqual(parse_page_args({'page': '   ', 'page_size': '\t'}), (1, 20, ''))

    def test_正常取值(self):
        self.assertEqual(parse_page_args({'page': '3', 'page_size': '50'}), (3, 50, ''))

    def test_非法_page_只报错不抛(self):
        for raw in ['abc', '0', '-1', '1.5', '1e3', '0x10', '一']:
            with self.subTest(raw=raw):
                page, size, error = parse_page_args({'page': raw})
                self.assertEqual((page, size), (0, 0))
                self.assertIn('page ', error)
                self.assertIn(repr(raw), error)

    def test_非法_page_size_只报错不抛(self):
        for raw in ['abc', '0', '-3']:
            with self.subTest(raw=raw):
                page, size, error = parse_page_args({'page_size': raw})
                self.assertEqual((page, size), (0, 0))
                self.assertIn('page_size', error)

    def test_两个都错时只说第一个(self):
        # 一次说两个错误对调用方更难读；这里锁的是「只报第一条」这个决定
        _page, _size, error = parse_page_args({'page': 'x', 'page_size': 'y'})
        self.assertIn('page ', error)
        self.assertNotIn('page_size', error)

    def test_page_size_超上限是夹紧不是报错(self):
        # 报错会把「翻到最后一页时顺手放大 page_size」的老客户端直接打断；
        # 夹紧只影响一次响应的体积，语义仍然正确。
        self.assertEqual(parse_page_args({'page_size': '999999'}), (1, MAX_PAGE_SIZE, ''))

    def test_上限为_0_或_None_时视为不设上限(self):
        self.assertEqual(parse_page_args({'page_size': '999999'}, max_page_size=0), (1, 999999, ''))
        self.assertEqual(parse_page_args({'page_size': '999999'}, max_page_size=None), (1, 999999, ''))

    def test_默认页大小可注入(self):
        self.assertEqual(parse_page_args({}, default_page_size=7), (1, 7, ''))

    def test_任何怪输入都不抛异常(self):
        # 这条是「永不抛异常」的兜底：值只要求能过 `.get`，别的什么都不假设
        weird = [None, '', ' ', '0', '-1', 'abc', '1.5', '١٢', '\\x00', '999999999999999999999999']
        for raw in weird:
            for key in ('page', 'page_size'):
                with self.subTest(key=key, raw=raw):
                    parse_page_args({key: raw})  # 不抛就算过


class DefaultPageSizeFromTests(unittest.TestCase):
    """从 `REST_FRAMEWORK` 那段配置里取默认页大小 —— 取不到就退到兜底值。"""

    def test_取得到就用它(self):
        self.assertEqual(default_page_size_from({'PAGE_SIZE': 7}), 7)
        self.assertEqual(default_page_size_from({'PAGE_SIZE': 100}), 100)

    def test_各种取不到都退到_20(self):
        # 期望值这里写**字面量 20**，不是 DEFAULT_PAGE_SIZE：
        # 引用被测常量本身等于「函数返回它自己」，恒真，锁不住任何东西。
        # 「模块里那个 20 只许有一处」由 SingleSourceTests 单独盯。
        for config in [None, 'x', 3, {}, {'PAGE_SIZE': None}, {'PAGE_SIZE': 0},
                       {'PAGE_SIZE': -5}, {'PAGE_SIZE': '20'}, {'PAGE_SIZE': True}]:
            with self.subTest(config=config):
                self.assertEqual(default_page_size_from(config), 20)

    def test_兜底常量就是_20(self):
        self.assertEqual(DEFAULT_PAGE_SIZE, 20)


class SlicePageTests(unittest.TestCase):
    """切页只有这一处 —— 「page 从 1 开始」这条约定也只该在这一处写。"""

    ITEMS = ['a', 'b', 'c', 'd', 'e']

    def test_第一页从下标_0_开始(self):
        self.assertEqual(slice_page(self.ITEMS, 1, 2), ['a', 'b'])

    def test_第二页(self):
        self.assertEqual(slice_page(self.ITEMS, 2, 2), ['c', 'd'])

    def test_最后一页不足一整页(self):
        self.assertEqual(slice_page(self.ITEMS, 3, 2), ['e'])

    def test_越界给空列表而不是报错(self):
        self.assertEqual(slice_page(self.ITEMS, 99, 2), [])

    def test_普通列表和元组都接受(self):
        # 因为有的调用点分的是 Redis 里取回来的 Python 列表，不是查询集
        self.assertEqual(slice_page(tuple(self.ITEMS), 2, 2), ('c', 'd'))


class _FakeRequest:
    def __init__(self, params):
        self.query_params = params


class PageParamsReadsSettingsTests(unittest.TestCase):
    """`page_params` 必须真的去读 `settings.REST_FRAMEWORK['PAGE_SIZE']`。

    这一段是本轮的核心：那句配置挂了很久没人读。只在函数里 `return DEFAULT_PAGE_SIZE`
    也能让上面所有用例通过，所以这里必须**把它读的那一层真的走一遍** ——
    用假的 `django.conf` 顶上去，不需要 Django settings、不需要数据库。

    （`pagination.py` 把 `from django.conf import settings` 放在函数体内，
    就是为了让这件事测得了。模块顶层一旦 import Django，`run_tests.py` 就带不动它。）
    """

    def setUp(self):
        self.fake = types.ModuleType('django.conf')
        self.fake.settings = types.SimpleNamespace()
        self.saved = sys.modules.get('django.conf')
        sys.modules['django.conf'] = self.fake
        self.addCleanup(self._restore)

    def _restore(self):
        if self.saved is None:
            sys.modules.pop('django.conf', None)
        else:
            sys.modules['django.conf'] = self.saved

    def _with_page_size(self, value):
        self.fake.settings.REST_FRAMEWORK = value

    def test_默认页大小跟着_settings_走(self):
        self._with_page_size({'PAGE_SIZE': 7})
        self.assertEqual(page_params(_FakeRequest({})), (1, 7, ''))

    def test_反向对照_改配置行为必须变(self):
        # 「它读了配置」和「它恰好返回 7」是两件事，这条把两者分开：
        # 同一次请求，只换配置，结果必须不同。删掉那次读，本用例立刻红。
        self._with_page_size({'PAGE_SIZE': 7})
        page, small, _ = page_params(_FakeRequest({}))
        self._with_page_size({'PAGE_SIZE': 40})
        page2, big, _ = page_params(_FakeRequest({}))
        self.assertEqual((page, page2), (1, 1))
        self.assertNotEqual(small, big)
        self.assertEqual((small, big), (7, 40))

    def test_settings_里没有那段配置时退到兜底(self):
        # 换掉整个 namespace，而不是 del 一个属性：settings 本来就可能没有这一段，
        # `del` 会把「配置缺失」写成「先得存在才能缺」。
        self.fake.settings = types.SimpleNamespace()
        self.assertEqual(page_params(_FakeRequest({})), (1, 20, ''))

    def test_上限夹紧在走_settings_时同样生效(self):
        self._with_page_size({'PAGE_SIZE': 7})
        self.assertEqual(page_params(_FakeRequest({'page_size': '1000'})), (1, MAX_PAGE_SIZE, ''))

    def test_非法参数在这一层就已经拦下(self):
        self._with_page_size({'PAGE_SIZE': 7})
        page, size, error = page_params(_FakeRequest({'page': 'abc'}))
        self.assertEqual((page, size), (0, 0))
        self.assertTrue(error)


class SingleSourceTests(unittest.TestCase):
    """结构锁：手抄的写法不许长回来，说好要分页的模块要真的在分页。"""

    INCANTATION = re.compile(r"query_params\s*\.\s*get\(\s*['\"](page|page_size)['\"]")
    MODULE = 'apps/utils/pagination.py'

    #: 手抄分页收敛之后，**应该**从 `pagination.py` 拿分页的模块。
    #: 这份清单是「两向对账」的一半：这里有、代码里没有 → 红；
    #: 代码里有、这里没登记 → 也红（新加的分页点必须当场被看见）。
    PAGINATING_MODULES = {
        'apps/ai_models/views.py',
        'apps/ai_models/upstream_views.py',
        'apps/api_proxy/views.py',
        'apps/dashboard/analytics_views.py',
        'apps/dashboard/views.py',
        'apps/image_gen/views.py',
        'apps/tickets/views.py',
        'apps/users/views.py',
        'apps/users/views_usage_log.py',
    }

    def test_扫描面真的扫到了东西(self):
        # 「没人再手抄分页参数」是**通行证式**断言：扫描面一旦变空，它照样全绿。
        # 这一轮就踩了一次 —— `parents[2]` 指到 `apps/` 而不是 `backend/`，
        # glob 一个文件都没扫到，而那条锁安静地通过了。所以把扫描面本身也钉住：
        # 文件数、必须包含的几个点、以及「tests 不在里面」。
        rels = sorted(rel for rel, _ in iter_sources())
        self.assertGreater(len(rels), 30, f'只扫到 {len(rels)} 个文件 —— 扫描面大概是错的')
        self.assertIn('apps/ai_models/views.py', rels)
        self.assertIn(self.MODULE, rels)
        self.assertEqual([r for r in rels if '/tests/' in r], [], 'tests 目录不该进扫描面')

    def test_没有任何地方再手抄分页参数(self):
        offenders = []
        for rel, text in iter_sources():
            if rel == self.MODULE:
                # 唯一允许把咒语当**反面教材**写出来的地方（抬头里引了一次）
                continue
            for number, line in enumerate(strip_comments(text).splitlines(), start=1):
                if self.INCANTATION.search(line):
                    offenders.append(f'{rel}:{number}')
        self.assertEqual(
            offenders, [],
            '这些地方又手抄了分页参数，改回 apps.utils.pagination：\n  ' + '\n  '.join(offenders),
        )

    def test_从_pagination_取分页的模块恰好是登记过的那批(self):
        found = set()
        for rel, text in iter_sources():
            if 'from apps.utils.pagination import' in text:
                found.add(rel)
        self.assertEqual(
            found, self.PAGINATING_MODULES,
            '与登记不符：多了 ' + repr(sorted(found - self.PAGINATING_MODULES)) +
            '，少了 ' + repr(sorted(self.PAGINATING_MODULES - found)),
        )

    def test_每个登记的模块都真的在分页(self):
        # 只 import 不调用是最高级的「看起来修好了」
        for rel in sorted(self.PAGINATING_MODULES):
            with self.subTest(module=rel):
                text = strip_comments((BACKEND / rel).read_text(encoding='utf-8'))
                self.assertTrue(
                    re.search(r'\b(paginate|slice_page|page_params)\s*\(', text),
                    f'{rel} import 了 pagination 却一次都没调用',
                )

    def test_20_这个默认值在代码里只有一处(self):
        # 用 AST 数字面量而不是文本搜索：抬头里引了一次 `'PAGE_SIZE': 20` 作反例，
        # 那是字符串，不该被算进来。剥注释不够，还得剥字符串。
        tree = ast.parse((BACKEND / self.MODULE).read_text(encoding='utf-8'))
        twenties = [
            node.lineno for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and node.value == 20 and not isinstance(node.value, bool)
        ]
        self.assertEqual(
            len(twenties), 1,
            f'模块代码里出现了 {len(twenties)} 个字面量 20（第 {twenties} 行）—— '
            '「默认每页多少条」只许有一处。',
        )

    def test_settings_里那份_PAGE_SIZE_与兜底值一致(self):
        # 「同一件事实写两处必然漂移」——既然后备值存在，就把它和 settings 里的值钉在一起：
        # 谁想单独改一边，这条会让他当场决定另一边怎么办。
        source = (BACKEND / 'config/settings.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        value = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == 'REST_FRAMEWORK' for t in node.targets
            ) and isinstance(node.value, ast.Dict):
                for key, item in zip(node.value.keys, node.value.values):
                    if isinstance(key, ast.Constant) and key.value == 'PAGE_SIZE':
                        value = item.value
        self.assertIsNotNone(value, "config/settings.py 里找不到 REST_FRAMEWORK['PAGE_SIZE']")
        self.assertEqual(
            value, DEFAULT_PAGE_SIZE,
            f'settings 写的是 {value}，pagination.py 的兜底值是 {DEFAULT_PAGE_SIZE} —— '
            '两个都自称「默认每页多少条」，不许各说各的。',
        )


class UsageLogViewSetTests(unittest.TestCase):
    """`/api/users/usage-logs/` 这条线：注册对了、真的分页了、重复实现没复活。"""

    def _module(self, rel):
        return (BACKEND / rel).read_text(encoding='utf-8')

    def test_usage_logs_仍然注册在用户侧路由上(self):
        urls = self._module('apps/users/urls.py')
        self.assertIn('usage-logs', urls)
        self.assertIn('APIAccessLogViewSet', urls)
        # 文件改名之后 import 必须跟着改 —— 旧名字还在就是重命名没做完
        self.assertNotIn('views_api_key', urls)

    def test_列表接口走的是统一分页(self):
        text = strip_comments(self._module('apps/users/views_usage_log.py'))
        tree = ast.parse(text)
        viewset = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'APIAccessLogViewSet'
        )
        methods = {n.name for n in viewset.body if isinstance(n, ast.FunctionDef)}
        self.assertIn(
            'list', methods,
            'APIAccessLogViewSet 没重写 list —— 那样会走 DRF 默认实现：裸数组、没有 total、'
            'page_size 也没有上限，前端只能写 `res.results || res || []` 去猜形状。',
        )
        list_source = next(
            n for n in viewset.body if isinstance(n, ast.FunctionDef) and n.name == 'list'
        )
        self.assertIn('paginate', {n.id for n in ast.walk(list_source) if isinstance(n, ast.Name)})

    def test_那份从未注册的重复实现没有复活(self):
        self.assertFalse(
            (BACKEND / 'apps/users/views_api_key.py').exists(),
            'views_api_key.py 又回来了 —— 那个文件里的 UserAPIKeyViewSet 从未被注册过，'
            '真正的实现在 apps/users/views.py::APIKeyViewSet（/users/keys/）。',
        )
        # 查**类的定义**而不是查这个名字：views_usage_log.py 的抬头里要写明
        # 「删掉的那个类叫什么」，那是散文，不是代码。按文本搜会把说明本身判成违规
        # —— 到时候人只会去删说明，不会去删重复实现。
        hits = sorted(
            rel for rel, text in iter_sources()
            if 'UserAPIKeyViewSet' in {
                node.name for node in ast.walk(ast.parse(text)) if isinstance(node, ast.ClassDef)
            }
        )
        self.assertEqual(hits, [], f'UserAPIKeyViewSet 又被定义了：{hits}')

    def test_密钥接口的实现在_views_py_那一份(self):
        # 两向对账的另一半：删掉重复实现之后，「谁在服务 /users/keys/」必须还是有答案的
        urls = self._module('apps/users/urls.py')
        self.assertIn("router.register(r'keys', APIKeyViewSet", urls.replace('"', "'"))
        self.assertIn('class APIKeyViewSet', self._module('apps/users/views.py'))


if __name__ == '__main__':
    unittest.main()
