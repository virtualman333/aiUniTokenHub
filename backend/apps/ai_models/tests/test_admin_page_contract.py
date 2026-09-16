# -*- coding: utf-8 -*-
"""「上游账号管理」页的字段契约（源码级，不连数据库、不需要 Django settings）。

为什么要一条**跨语言**的锁
--------------------------
这一页上有 6 个列/卡片曾经绑在**响应里根本不存在的键**上：

    weight / max_qps / total_calls / success_rate / avg_latency

而 `UpstreamAccountListSerializer` 原本只返回 11 个字段，`UpstreamAccount` 模型上
更是连 `total_calls` 这几个列都没有（它们在 `ModelUpstreamAccount` 绑定上）。
前端每处都写了兜底（`row.total_calls || 0`、`Number(row.success_rate || 0).toFixed(1)`），
所以**不报错、不崩、只是永远显示 0**：调用次数 0、成功率红色的 0.0%、
平均延迟 0ms，而同一页的汇总卡片按 `|| 100` 兜底显示 100.0% ——
同一页两个数字互相矛盾，谁都发现不了。

后端单测覆盖不到 Vue 模板，前端构建也不会因为「读了个不存在的键」而报错
（`undefined` 一路静默通过）。所以这层锁只能扫源码文本，按**三种不同的数据来源**
分别对账（它们的合同方不是同一个接口）：

  1. 账号表格      → `UpstreamAccountListSerializer.Meta.fields`（GET 列表）
  2. 新增/编辑弹窗 → `UpstreamAccountSerializer.Meta.fields`（POST / PATCH 的载荷）
  3. 绑定模型弹窗  → `upstream_views.model_list` 返回的字典键

跑法（在 backend/ 下）：python run_tests.py
"""
import re
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
REPO = BACKEND.parent

SERIALIZER = BACKEND / 'apps' / 'ai_models' / 'upstream_serializers.py'
VIEWSET = BACKEND / 'apps' / 'ai_models' / 'upstream_views.py'
PROXY = BACKEND / 'apps' / 'api_proxy' / 'views_openai.py'
PAGE = REPO / 'frontend' / 'src' / 'views' / 'admin' / 'ChannelManagement.vue'


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='replace')


def serializer_fields(cls_name: str) -> set:
    """从序列化器源码里取 `Meta.fields`（不 import，免得要 Django settings）"""
    src = read(SERIALIZER)
    start = src.index(f'class {cls_name}(')
    meta = src.index('fields = [', start)
    body = src[meta:src.index(']', meta)]
    return set(re.findall(r"'([a-z_]+)'", body))


def function_body(src: str, signature: str, indent: str = '') -> str:
    """取一段函数体（按缩进切到下一个同级 `def` / `class`）"""
    start = src.index(signature)
    tail = src[start + len(signature):]
    for m in re.finditer(r'(?m)^' + re.escape(indent) + r'(def |class )', tail):
        return tail[:m.start()]
    return tail


def blocks(text: str, open_tag: str) -> list:
    """粗略切出成对标签之间的块（本页这两种标签不嵌套，够用）"""
    out = []
    pos = 0
    while True:
        i = text.find(open_tag, pos)
        if i < 0:
            return out
        j = text.find('</el-table>', i)
        out.append(text[i:j if j > 0 else len(text)])
        pos = i + 1


def main_table(page: str) -> str:
    """账号表格 —— 判据是「这一块里出现了 bindings 的表格数据是 channels」"""
    for blk in blocks(page, '<el-table '):
        if ':data="channels"' in blk:
            return blk
    raise AssertionError('找不到账号表格（:data="channels"）—— 页面结构变了？这条锁需要跟着改')


def model_table(page: str) -> str:
    for blk in blocks(page, '<el-table '):
        if ':data="modelList"' in blk:
            return blk
    raise AssertionError('找不到绑定模型弹窗的表格（:data="modelList"）')


def form_items(page: str) -> str:
    """新增/编辑弹窗（这里的 prop 是 el-form-item 的校验键，对应表单载荷）"""
    i = page.index('<el-dialog')
    return page[i:page.index('</el-dialog>', i)]


def row_keys(block: str) -> set:
    return set(re.findall(r'\brow\.([a-zA-Z_][a-zA-Z0-9_]*)', block))


class 账号表格Test(unittest.TestCase):
    """模板里读的每个键，列表接口都得真的返回"""

    def setUp(self):
        self.fields = serializer_fields('UpstreamAccountListSerializer')
        self.table = main_table(read(PAGE))

    def test_每一列的prop都在列表序列化器里(self):
        # `prop="x"` 是 el-table-column 的取值键。不在 fields 里 = 这一列永远是空的
        props = set(re.findall(r'prop="([^"]+)"', self.table))
        self.assertTrue(props, '没扫到任何 prop —— 页面结构变了？')
        missing = sorted(p for p in props if p not in self.fields)
        self.assertEqual(
            missing, [],
            f'这些列绑在了响应里没有的键上，页面会一直显示 0/空：{missing}\n'
            f'序列化器实际返回：{sorted(self.fields)}'
        )

    def test_单元格模板里读的每个row键也在列表序列化器里(self):
        # `prop` 只管列头，单元格模板里还常常直接读 `row.x` —— 那一路没有 prop 兜着，
        # 漏了同样静默（原来「平均延迟」就是 row.avg_latency）
        missing = sorted(k for k in row_keys(self.table) if k not in self.fields)
        self.assertEqual(missing, [], f'表格里读了响应里没有的键：{missing}')

    def test_统计字段都在响应里(self):
        # 正向确认：修复后的四个统计键必须真的在响应里
        for key in ('total_calls', 'error_count', 'success_rate', 'last_used'):
            self.assertIn(key, self.fields, f'{key} 应当在列表响应里')

    def test_编辑弹窗要预填的字段都在响应里(self):
        # 列表里不给 max_tpm / proxy_url，编辑弹窗就会退回表单默认值
        # （max_tpm 变 100000、proxy_url 变空），一保存等于把真实配置静默改掉
        for key in ('max_tpm', 'proxy_url', 'max_rpm', 'order'):
            self.assertIn(key, self.fields, f'{key} 要在列表响应里，否则编辑弹窗预填不出来')

    def test_没有数据源的列不许回到页面上(self):
        # 这两个键在全仓库都不存在，也没有任何地方会写 —— 加回来就是又摆一排假数字
        for key in ('avg_latency', 'max_qps'):
            self.assertNotIn(key, self.table, f'{key} 没有任何数据源，不该出现在表格里')
        self.assertNotIn('prop="weight"', self.table, '账号级没有 weight（权重在绑定上）')


class 编辑弹窗Test(unittest.TestCase):
    """表单 prop 对应的是写入载荷，合同方是写入序列化器"""

    def setUp(self):
        self.fields = serializer_fields('UpstreamAccountSerializer')
        self.form = form_items(read(PAGE))

    def test_表单项的prop都在写入序列化器里(self):
        props = set(re.findall(r'prop="([^"]+)"', self.form))
        self.assertTrue(props, '没扫到任何表单项 —— 弹窗结构变了？')
        missing = sorted(p for p in props if p not in self.fields)
        self.assertEqual(missing, [], f'这些表单项后端不认：{missing}（写入序列化器里没有）')

    def test_编辑用PATCH且留空不覆盖密钥(self):
        # `api_key` 是 write_only，列表拿不回来 —— 整体 PUT 会把空串发上去，
        # 后端 allow_blank=False 直接 400，编辑按钮从来没成功过
        page = read(PAGE)
        block = page[page.index('const submitForm'):]
        block = block[:block.index('const testChannel')]
        self.assertIn('api.patch(', block, '编辑应当走 PATCH（PUT 会带空 api_key 被 400 挡下）')
        self.assertNotIn('api.put(', block, '不要回到整体 PUT')
        self.assertIn('delete payload.api_key', block, '留空必须表示「不修改」，而不是发一个空串')


class 绑定模型弹窗Test(unittest.TestCase):
    """这一块的合同方是 model_list 这个 action 返回的字典"""

    def setUp(self):
        self.table = model_table(read(PAGE))
        body = function_body(read(VIEWSET), 'def model_list(self', indent='    ')
        self.keys = set(re.findall(r"'([a-z_]+)':", body))

    def test_弹窗里的键由model_list提供(self):
        self.assertTrue(self.keys, '没扫到 model_list 返回的字典键 —— 这个 action 改名了？')
        props = set(re.findall(r'prop="([^"]+)"', self.table))
        missing = sorted(p for p in props if p not in self.keys)
        self.assertEqual(missing, [], f'绑定模型弹窗读了 model_list 没返回的键：{missing}')

    def test_弹窗里读的row键也由model_list提供(self):
        missing = sorted(k for k in row_keys(self.table) if k not in self.keys)
        self.assertEqual(missing, [], f'绑定模型弹窗读了 model_list 没返回的键：{missing}')


class 统计写入Test(unittest.TestCase):
    """22 个调用点曾经全是空操作 —— 这条锁钉住「别再退化回去」"""

    def setUp(self):
        self.body = function_body(read(PROXY), 'def update_upstream_usage(')

    def test_不再靠hasattr做静默空操作(self):
        # 修复前：UpstreamAccount 上没有 usage_count 字段，hasattr 恒为 False，
        # 于是这个函数每一次都直接 return —— 记了 22 个调用点，一条都没记上
        self.assertNotIn(
            "hasattr(account, 'usage_count')", self.body,
            '又出现了「有没有这个字段」的静默兜底 —— 统计会在无提示的情况下全部记不上'
        )

    def test_写回的是绑定而不是账号(self):
        # 计数只在 ModelUpstreamAccount 上，账号表没有这几列
        self.assertIn('ModelUpstreamAccount.objects', self.body, '统计必须写回绑定表')
        self.assertIn("F('usage_count')", self.body, '计数要在库里自增（F 表达式），避免并发读改写丢计数')
        self.assertIn("F('error_count')", self.body)
        self.assertIn('last_used', self.body)

    def test_增量口径来自公共模块(self):
        # 写入侧（+1/+1）与读取侧（分母是 usage 不是 usage+error）必须同一份口径
        self.assertIn('usage_delta', self.body, '增量应当来自 apps.utils.channel_stats，别在这里手写')
        self.assertNotIn('+= 1', self.body, '不要回到「读出来 +1 再整体 save」的写法')


class 选中账号Test(unittest.TestCase):
    """选完账号就把绑定丢了 —— 统计无处可写"""

    def setUp(self):
        self.body = function_body(read(PROXY), 'def select_upstream_account(')

    def test_选中时把绑定挂在返回的账号上(self):
        self.assertIn('selected.selected_binding = selected_binding', self.body,
                      '必须把绑定的引用带出去，否则 update_upstream_usage 拿不到')

    def test_池子里存的是绑定不是裸账号(self):
        # 旧形态 `accounts_pool.append((account, binding.weight))` 把绑定对象当场丢掉，
        # 后面 `accounts_pool[0][0]` 只能拿到账号 —— 统计从此没有落点
        self.assertNotIn('accounts_pool[0][0]', self.body, '又退回到「只留账号」的写法了')
        self.assertNotIn('for _, weight in accounts_pool', self.body)


class 聚合注记Test(unittest.TestCase):
    """统计字段不在账号表上，必须由视图层一次聚合出来"""

    def setUp(self):
        self.body = function_body(read(VIEWSET), 'def get_queryset(self):', indent='    ')

    def test_视图层聚合了三个统计(self):
        for agg in ("Sum('model_bindings__usage_count')", "Sum('model_bindings__error_count')",
                    "Max('model_bindings__last_used')"):
            self.assertIn(agg, self.body, f'列表需要 {agg}，否则序列化器读不到值')


class 成功率口径Test(unittest.TestCase):
    """成功率只有一个定义处 —— 写入侧 / 读取侧 / 展示侧不许各写一套"""

    def test_序列化器用公共模块算成功率(self):
        src = read(SERIALIZER)
        self.assertIn('from apps.utils.channel_stats import success_rate', src)
        self.assertIn('success_rate(', src, '序列化器应当调公共模块，而不是自己算')
        # 自己算就会出现第二套分母
        self.assertNotIn('* 100', src, '序列化器里不该再手写百分数算式')

    def test_管理页汇总不平均每行成功率(self):
        # 对每行 success_rate 求平均是另一套算法：从没调用过的行会按 100% 参与平均，
        # 两张卡片和表格里的数字对不上。必须先用原始计数加总，再算一次比率。
        page = read(PAGE)
        start = page.index('// 汇总口径')
        block = page[start:page.index('} catch', start)]
        self.assertIn('error_count', block, '汇总必须基于 error_count 原始计数')
        self.assertNotIn('c.success_rate', page, '又出现「对每行成功率求平均」了')
