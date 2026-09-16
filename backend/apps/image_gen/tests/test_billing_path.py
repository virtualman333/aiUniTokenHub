# -*- coding: utf-8 -*-
"""
图片生成扣费路径的「不许回退」锁（纯 Python，不依赖 Django settings 与数据库）

为什么用读源码的方式锁
----------------------
本仓库的单元测试契约是**不连数据库**（见 AGENTS.md）。而这里要锁的事情 ——
「扣费是否在事务与行锁内」「余额不足时图有没有先落库」「保存图片失败有没有退款」——
全都发生在数据库操作里，靠 unittest 跑不出来。既然跑不出来，就用断言把源码里
那几行关键结构钉住：它们一旦被改回老写法，测试立刻红。

这不是万能锁，它锁的是**结构**而不是**行为**。行为层面的正确性仍然依赖
代码评审 —— 但至少「有人悄悄把行锁删掉」「有人把保存图片挪回扣费之前」
「有人把失败路径的退款去掉」这几种回退不会再无声无息地发生。
纯逻辑部分（文案与金额规则）另有 `test_billing_messages.py` 真正跑行为。

跑法（在 backend/ 下，不需要数据库）：
    python run_tests.py
"""
import ast
import importlib.util
import re
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]

IMAGE_VIEWS = BACKEND / 'apps' / 'image_gen' / 'views.py'
IMAGE_PRICING = BACKEND / 'apps' / 'image_gen' / 'pricing.py'
# 计费文案与金额规则的家：从 `apps/image_gen/billing.py` 搬到 `apps/utils/billing.py`
# （图片路径与两个 OpenAI 兼容端点都要用同一张表）。这里跟着改路径，
# 而不是让锁去猜两个可能的位置 —— 位置本身就是「只有一个家」的一部分。
UTILS_BILLING = BACKEND / 'apps' / 'utils' / 'billing.py'
OPENAI_VIEWS = BACKEND / 'apps' / 'api_proxy' / 'views_openai.py'
RESPONSES_VIEWS = BACKEND / 'apps' / 'api_proxy' / 'views_responses.py'


def _read(path: Path) -> str:
    assert path.exists(), f'读不到 {path} —— 文件被挪走了？这条锁需要跟着改'
    return path.read_text(encoding='utf-8')


def _func_body(src: str, name: str) -> str:
    """抠出一个函数 / 方法的正文：从 `def name(` 到同级或更外层的下一个 def/class。

    兼容**方法**（有缩进）与顶层函数。只按顶层的 `^def` 找会漏掉前者 ——
    那时锁会红在「找不到目标」上，而不是红在它想守的规则上，属于假红（假结论）。
    """
    m = re.search(rf'^([ \t]*)def {name}\(', src, re.M)
    assert m, f'找不到函数 {name} —— 改名了？这条锁需要跟着改'
    indent = m.group(1)
    rest = src[m.end():]
    nxt = re.search(rf'^[ \t]{{0,{len(indent)}}}(?:def |class |@)', rest, re.M)
    end = m.end() + nxt.start() if nxt else len(src)
    body = src[m.start():end]
    assert len(body) > 200, f'{name} 只抠到 {len(body)} 个字符，正则大概失效了 —— 这条锁形同虚设'
    return body


def _strip_strings(src: str) -> str:
    """去掉三引号字符串，只留代码。

    这个 helper 是从两次真实误报里长出来的：函数的 docstring 里往往**引用着
    旧实现**（`_deduct_cost` 的 docstring 里就有 `return cost, False`，
    同一文件下面那条 Bill 断言也被 docstring 里的 `Bill.objects.create(...)`
    带偏过）。对着整段源码做字符串/正则断言，命中的可能就是那段注释 ——
    测出个假的结论，还很难看出来。凡是要断言「代码里有没有某个写法」，先过这里。
    """
    return re.sub(r'"""(?:.|\n)*?"""', '', src)


def _resolve_imports(src: str, src_path: Path) -> dict:
    """`from <模块> import a, b` → `{解析到的文件: {名字}}`。

    两种写法都认，且**都解析成真实文件**：

    - 绝对导入 `from apps.utils.billing import x` → `apps/utils/billing.py`；
    - 相对导入 `from .billing import x` → **按导入方所在目录**解析。

    为什么非要把相对导入解析成文件、而不是只比「最后一段名字」：那样
    `.billing` 与 `apps.utils.billing` 会被当成同一件事，于是「文件被删掉/搬走、
    导入指向了别处」这种线上 500 也照样绿。这是负向验证逼出来的修正 ——
    第一次写的时候只比名字，注入 `from .billing import ...`（文件已不存在）
    时锁全绿，等于没锁。
    """
    out: dict = {}
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.ImportFrom):
            continue
        names = {alias.name for alias in node.names}
        if node.level == 0:
            if not node.module:
                continue
            resolved = BACKEND.joinpath(*node.module.split('.')).with_suffix('.py')
        else:
            base = src_path.parent
            for _ in range(node.level - 1):
                base = base.parent
            resolved = base
            for part in (node.module or '').split('.'):
                resolved = resolved / part
            resolved = resolved.with_suffix('.py')
        out.setdefault(resolved, set()).update(names)
    return out


def _load_pure_module(path: Path):
    """把纯 Python 模块从文件路径加载进来（不走 package，因此不触发 apps 的 __init__）。"""
    spec = importlib.util.spec_from_file_location(f'vca_pure_{path.stem}', path)
    assert spec and spec.loader, f'加载不了 {path}'
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ImageBillingIsAtomicTest(unittest.TestCase):
    """图片扣费必须和 LLM 扣费一样是原子的"""

    def setUp(self):
        self.views = _read(IMAGE_VIEWS)
        self.body = _func_body(self.views, '_deduct_cost')

    def test_扣费在事务里(self):
        self.assertIn('transaction.atomic()', self.body)

    def test_扣费在行锁里(self):
        # 没有 select_for_update 就是裸的读-改-写：并发下两个请求读到同一个余额、
        # 双双通过校验、各扣一次，少扣的部分平台收不回来
        self.assertIn('select_for_update()', self.body)

    def test_扣款与记账在同一事务内(self):
        # 只能在 `transaction.atomic()` **之后**那一段里找 Bill ——
        # 函数的 docstring 里引用着旧代码，也含 `Bill.objects.create(...)`，
        # 直接 index() 会命中 docstring，测出个假的顺序。
        atomic_at = self.body.index('transaction.atomic(')
        self.assertIn(
            'Bill.objects.create(', self.body[atomic_at:],
            '记账必须在事务块里（否则扣了钱可能没有账单）',
        )

    def test_余额是在锁内重新读的_而不是用调用方传进来的对象判断(self):
        # 用 user.balance（调用方的旧快照）判断，锁就白加了
        locked_at = self.body.index('select_for_update()')
        after_lock = self.body[locked_at:]
        self.assertIn('locked.balance <', after_lock)

    def test_余额不足时一分不扣(self):
        # 判断在写余额之前：先 return False 才允许走到减法
        guard_at = self.body.index('locked.balance <')
        sub_at = self.body.index('locked.balance - cost')
        self.assertLess(guard_at, sub_at, '余额判断必须排在扣减之前')


class ImageBillingSingleSourceTest(unittest.TestCase):
    """定价规则只能有一个来源"""

    def setUp(self):
        self.views = _read(IMAGE_VIEWS)

    def test_views里不再出现兜底单价的字面量(self):
        # 0.08 只应出现在 pricing.py；views 里再写一遍就是第二份实现，必然漂移
        self.assertNotRegex(self.views, r'0\.08', '兜底单价又被写进了 views.py，请改用 pricing.image_cost')

    def test_views不再直接读per_image_price字段(self):
        # 直接读字段 = 绕开 pricing 里的「0 表示没配」规则
        self.assertNotIn('per_image_price', self.views, '请改用 pricing.unit_price_of / image_cost')

    def test_前后两处校验都走同一个定价函数(self):
        # 前置余额校验与真正扣费各要调用一次
        self.assertGreaterEqual(
            self.views.count('image_cost('), 2,
            '前置校验与扣费应各自调用 image_cost()，否则又会退化成两份算式',
        )


class InsufficientBalanceLeavesNoImagesTest(unittest.TestCase):
    """余额不足时，图片不能已经落库"""

    def test_扣费排在保存图片之前(self):
        src = _read(IMAGE_VIEWS)
        self.assertIn('_deduct_cost(request.user', src)
        self.assertIn('GeneratedImage.objects.create', src)
        deduct_at = src.index('_deduct_cost(request.user')
        save_at = src.index('GeneratedImage.objects.create')
        self.assertLess(
            deduct_at, save_at,
            '扣费必须排在保存图片之前：反过来会让「余额不足」的请求已经留下图片，'
            '用户从历史里照样能下载 —— 白拿，上游成本由平台付',
        )


class BothBillingPathsStayInSyncTest(unittest.TestCase):
    """同一件事（扣费）两处实现，不许单边漂移"""

    def test_两条扣费路径都用了行锁(self):
        cases = {
            'image_gen._deduct_cost': _read(IMAGE_VIEWS),
            'views_openai.calculate_and_deduct_cost': _read(OPENAI_VIEWS),
        }
        for label, src in cases.items():
            with self.subTest(path=label):
                body = _func_body(src, '_deduct_cost' if label.startswith('image_gen') else 'calculate_and_deduct_cost')
                self.assertIn('select_for_update()', body, f'{label} 缺行锁，与另一条扣费路径不一致')
                self.assertIn('transaction.atomic()', body, f'{label} 缺事务')


class RelativeImportContractTest(unittest.TestCase):
    """views 从纯模块 import 的名字必须真的存在，而且必须指向那个文件

    为什么需要这一条
    ----------------
    本仓库的单元测试不装 Django（`python run_tests.py` 起不来库，也 import 不了
    任何含 `models` 的模块）。于是 `image_gen/views.py` 顶部的
    `from apps.utils.billing import (...)` 写错一个名字，**在这个环境里没有任何
    测试会发现** —— 而线上是每一次图片请求都 500。这是纯文本断言补不上的一层：
    文本测试只能看见那行字，看不见那个名字到底存不存在。

    好在 `billing.py` 与 `pricing.py` 是纯 Python（把它们拆出来本来就有这个意义），
    可以真的加载进来、按名字核对。带 Django 的模块（`.models` 等）这里不碰。

    这里连带核对**指向哪个文件**：计费模块从 `apps/image_gen/` 搬到
    `apps/utils/` 之后，`from .billing import x` 这种写法在文本上「看起来也对」，
    但解析到的是另一个文件（或者干脆不存在）。只比名字最后一段的话，
    「文件搬走、导入没跟着改」会全绿，线上却每次请求都炸。
    """

    def _assert_names_exist(self, src_path, target_path) -> None:
        targets = _resolve_imports(_read(src_path), src_path)
        self.assertTrue(targets, f'{src_path.name} 里一条 `from ... import` 都没解析到 —— 这条锁需要跟着改')
        hit = targets.get(target_path)
        self.assertTrue(
            hit,
            f'{src_path.name} 里没有任何 import 指向 {target_path.name}；'
            f'实际指向的是 {[str(p) for p in targets if p.name == target_path.name] or "别处"}',
        )
        module = _load_pure_module(target_path)
        for name in sorted(hit):
            with self.subTest(src=src_path.name, name=name):
                self.assertTrue(
                    hasattr(module, name),
                    f'{src_path.name} 从 {target_path.name} 导入了不存在的名字 {name} —— '
                    f'纯文本测试看不见这个，线上会直接 500',
                )

    def test_图片views从计费模块导入的名字都存在(self):
        self._assert_names_exist(IMAGE_VIEWS, UTILS_BILLING)

    def test_图片views从pricing导入的名字也存在(self):
        self._assert_names_exist(IMAGE_VIEWS, IMAGE_PRICING)

    def test_两个代理views从计费模块导入的名字都存在(self):
        for path in (OPENAI_VIEWS, RESPONSES_VIEWS):
            with self.subTest(view=path.name):
                self._assert_names_exist(path, UTILS_BILLING)

    def test_计费模块在共用包里_不在image_gen里(self):
        # 「只有一个家」的机械保证：老位置不许留副本（留着副本，两条路径就可能
        # 各自 import 一份，改一处另一处不动）。文案模块搬家这件事本身也要上锁。
        self.assertFalse(
            (BACKEND / 'apps' / 'image_gen' / 'billing.py').exists(),
            'image_gen 下又出现了一份 billing.py —— 计费文案只该有 apps/utils/billing.py 一处',
        )
        self.assertTrue(UTILS_BILLING.exists())


class DeductResultIsNotBooleanTest(unittest.TestCase):
    """扣费结果是三档，不许退化成布尔值

    「失败」本来有两种：余额不足（用户充值可解）与服务端出错（用户充值没用）。
    合成一个 False 之后，调用方只能回一句「余额不足」—— 余额充足的人被告知去
    充值，真正的问题被伪装成 400，前端既不提示异常也不重试。
    """

    def setUp(self):
        self.src = _read(IMAGE_VIEWS)
        self.body = _func_body(self.src, '_deduct_cost')

    def test_扣费不再返回布尔值(self):
        # 只在**代码**里找：_deduct_cost 的 docstring 正引用着那段旧实现
        # （里面就有 `return cost, False`），对着整段断言会命中它、测出个假结论。
        code = _strip_strings(self.body)
        self.assertNotRegex(
            code, r'return cost, (True|False)\b',
            '扣费结果又退回布尔值了 —— 那样「余额不足」与「服务端出错」就只剩一种说法',
        )

    def test_三档结果都用上了(self):
        # 只看代码：docstring 里也写着这三个名字（解释这次改动），
        # 不过滤掉的话，把某档从代码里删掉、这条断言还是绿的。
        code = _strip_strings(self.body)
        for name in ('DEDUCT_OK', 'DEDUCT_INSUFFICIENT', 'DEDUCT_ERROR'):
            with self.subTest(name=name):
                self.assertIn(name, code)

    def test_用户可见文案全部来自billing(self):
        # 旧写法是把「余额不足」这句字面量直接回给用户；现在一律经 billing 出。
        # 同样只看代码，不看注释 —— 注释里提这些词是正常的说明。
        code = _strip_strings(self.src)
        self.assertNotIn("'余额不足'", code, '「余额不足」又被写成字面量了，请改用 billing.insufficient_message')
        self.assertNotIn('未产生', code, '文案被复制进 views.py 了，请改用 billing.deduct_failure')
        for fn in ('insufficient_message(', 'deduct_failure(', 'refund_message('):
            with self.subTest(fn=fn):
                self.assertIn(fn, code)

    def test_文案模块保持纯Python(self):
        # 一旦 billing.py 依赖 Django，这些文案就只能连库才测得了（MySQL 测试库起不来）。
        # 只看真正的 import 行：docstring 里正大光明写着「不 import Django」。
        imports = [
            line.strip() for line in _read(UTILS_BILLING).splitlines()
            if line.strip().startswith(('import ', 'from '))
        ]
        self.assertTrue(imports, 'billing.py 里一条 import 都没抓到 —— 这条锁需要跟着改')
        for line in imports:
            with self.subTest(line=line):
                self.assertNotRegex(line.lower(), r'django|transaction', f'{line} —— 文案模块必须保持纯 Python')


class RefundPathTest(unittest.TestCase):
    """「钱扣了、图没存下」必须有兜底：退款 + 记录改成 failed"""

    def setUp(self):
        self.src = _read(IMAGE_VIEWS)
        self.body = _func_body(self.src, '_refund_cost')

    def test_退款在事务与行锁里(self):
        self.assertIn('transaction.atomic()', self.body)
        self.assertIn('select_for_update()', self.body)

    def test_退款写的是refund类型的账单(self):
        # 用户端账单页早就把「退款」的样式写好了，模型里也有这个类型，
        # 但后端一条都没产生过 —— 正是这条断言让「用户真的能在账单里看到退款」
        # 从「模型里有」变成「代码会写」
        self.assertIn("type='refund'", self.body)

    def test_退款与把费用归零在同一事务内(self):
        # 归零同时就是幂等标记：第二次调用读到 0 就退不出第二遍，
        # 不需要为此加字段和迁移。
        #
        # ⚠ 断言必须精确到 **locked_gen** 那一行。函数末尾还有一句
        # `generation.cost = Decimal('0')`（把内存对象同步一下，在事务之外），
        # 只断言 "cost = Decimal('0')" 的话，删掉事务里那句、这条锁照样是绿的 ——
        # 那就等于没锁。这是靠注入验证才发现的。
        atomic_at = self.body.index('transaction.atomic(')
        self.assertIn("type='refund'", self.body[atomic_at:])
        self.assertIn(
            "locked_gen.cost = Decimal('0')", self.body[atomic_at:],
            '退款没有在事务里把那笔费用归零 —— 幂等标记没了，重复调用会退两次',
        )

    def test_退款金额要重新在锁内读(self):
        # 用调用方传进来的旧快照判断金额，行锁就白加了
        lock_at = self.body.index('select_for_update()')
        self.assertIn('refund_amount_of(locked_gen.cost)', self.body[lock_at:])

    def test_锁顺序与扣费一致_先用户再生成记录(self):
        # _deduct_cost 是先锁 User、再落 generation 那行；退款要是反着来，
        # 并发下一个走扣费一个走退款就可能互相等对方的行锁 —— 死锁
        user_lock = self.body.index('User.objects.select_for_update()')
        gen_lock = self.body.index('ImageGeneration.objects.select_for_update()')
        self.assertLess(user_lock, gen_lock, '退款把锁顺序反过来了，与 _deduct_cost 不一致')

    def test_退款失败不再抛异常(self):
        # 退款失败已经是最坏的情况：这时要把「没退成」如实记进日志，
        # 而不是再抛一个异常把真正的失败原因盖掉
        exc_at = self.body.index('except Exception')
        self.assertIn('return Decimal', self.body[exc_at:])
        self.assertNotIn('raise', self.body[exc_at:])

    def test_退款只可能发生在扣费之后(self):
        # ⚠ 不能直接 src.index('_refund_cost(generation)')：函数**定义**那一行
        # 也是这个字符串，会命中定义处、得出「退款排在扣费之前」的假结论。
        # 所以从扣费那一行往后找**调用点**。
        deduct_at = self.src.index('_deduct_cost(request.user')
        refund_call_at = self.src.index('_refund_cost(generation)', deduct_at)
        self.assertLess(deduct_at, refund_call_at, '退款排在扣费之前 —— 那会退一笔根本没扣的钱')

    def test_保存图片失败时确实调了退款并改成failed(self):
        # 锚在 logger 那一行往后看：不能锚在 '图片保存失败' 上，因为它第一次出现
        # 是 refund_message(refunded, '图片保存失败')，在退款调用**之后**。
        except_at = self.src.index('[ImageGen] 保存图片失败 generation_id')
        window = self.src[except_at:except_at + 900]
        self.assertIn('_refund_cost(', window, '保存图片失败后没有退款 —— 用户付了钱，什么都没拿到')
        self.assertIn("status = 'failed'", window, '失败后没改成 failed，记录会永远停在「生成中」')

    def test_保存图片那段被try包住(self):
        # 保存图片要写磁盘、写数据库，会失败。没被 try 包住的话，
        # 一旦失败就是「请求 500 + 钱照扣 + 不退款 + 记录停在 pending」。
        try_at = self.src.index('try:', self.src.index('_deduct_cost(request.user'))
        save_at = self.src.index('GeneratedImage.objects.create')
        except_at = self.src.index('图片保存失败')
        self.assertLess(try_at, save_at, '保存图片不在 try 块里')
        self.assertLess(save_at, except_at, '兜异常的 except 不在保存图片之后')


def _docstring_nodes(tree: ast.AST) -> set:
    """模块 / 类 / 函数的第一条语句若是字符串，它就是个 docstring（不是文案）"""
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, 'body', [])
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            out.add(id(first.value))
    return out


_LOG_METHODS = frozenset({'debug', 'info', 'warning', 'error', 'critical', 'exception', 'log'})


def _log_string_ids(tree: ast.AST) -> set:
    """`logger.xxx(...)` 里用到的字符串常量的 id。

    为什么要把日志单独摘出来：这一轮要锁的是「**给用户看的话**不许在 views 里
    再写一份」，而日志里出现「余额不足」是**对的** —— 入口那句话说的就是事实
    （它按 balance<=0 判的）。把日志也算进去，锁就红在正确的地方，
    然后下一个人只会把断言放宽而不再修复真问题。
    """
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr not in _LOG_METHODS:
                continue
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                for inner in ast.walk(arg):
                    if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                        out.add(id(inner))
    return out


def _code_strings(src: str) -> list:
    """源码里可能**到达用户**的字符串字面量（注释、docstring、日志都不在内）。

    为什么走 AST 而不是正则：这一轮把「计费文案不许在 views 里写第二遍」的锁
    从图片路径扩到两个代理端点，而那两个文件的**注释和 docstring 里正引着旧文案**
    （解释这次改了什么）。用正则/`in` 去断言，命中的就是那句说明 —— 测出个假结论，
    而且很难看出来。注释本来就不进 AST；docstring 是字符串常量，日志调用单独摘掉
    （见 `_log_string_ids`）。
    """
    tree = ast.parse(src)
    skip = _docstring_nodes(tree) | _log_string_ids(tree)
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in skip
    ]


def _called_names(src: str) -> set:
    """源码里被调用的函数名（AST 取，注释与 docstring 天然不在其中）。

    用来断言「这一段真的调用了某个函数」，比 `assertIn('foo(', src)` 可靠：
    后者会被注释里的一句 `foo(` 骗过去。
    """
    names = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _call_count(src: str, name: str) -> int:
    n = 0
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (isinstance(func, ast.Name) and func.id == name) or (
            isinstance(func, ast.Attribute) and func.attr == name
        ):
            n += 1
    return n


def _balance_gate_count(src: str) -> int:
    """`if <user>.balance <= 0:` 形式的入口余额闸门有几处。

    与 `_call_count(src, 'precheck_failure')` 配对使用：**每一道闸门都必须在同一张
    表里取话**。只断言「这个文件调用过 precheck_failure」是不够的 —— 两个端点各有
    两处闸门，改掉其中一处、另一处还留着，那条断言照样绿（这是负向验证发现的：
    第一次就是这么漏的）。
    """
    n = 0
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.If):
            dumped = ast.dump(node.test)
            if 'balance' in dumped and 'LtE' in dumped:
                n += 1
    return n


class ChatBillingCopyIsSharedTest(unittest.TestCase):
    """两个 OpenAI 兼容端点：计费失败也必须经同一张翻译表

    AGENTS.md 早写着两条规则：「服务端扣费失败不得报成余额不足」「用户可见的
    计费文案只有一个家」。但在此之前，这两条**只有图片路径遵守** —— 规则留在
    文档里，没有任何东西执行它，于是代理侧一直回着 402 +「余额不足，请充值后
    再试。」，而 `calculate_and_deduct_cost` 返回 `False` 的三条路径里没有一条
    是余额不足。这一组就是那两条规则的可执行版本。
    """

    def setUp(self):
        self.files = {
            'views_openai.py': _read(OPENAI_VIEWS),
            'views_responses.py': _read(RESPONSES_VIEWS),
        }

    def test_代码里不许再出现计费文案字面量(self):
        # 只看可能到达用户的字符串：注释/docstring 里引着旧文案是正常的说明，
        # 日志里说「余额不足」也是对的（入口那句是按 balance<=0 判的事实）。
        banned = ('余额不足', '请充值', '未产生费用', '扣费失败')
        for name, src in self.files.items():
            with self.subTest(file=name):
                found = [s for s in _code_strings(src) if any(b in s for b in banned)]
                self.assertEqual(
                    found, [],
                    f'{name} 里又出现了计费文案字面量 {found} —— '
                    f'请改用 apps.utils.billing（同一句话两处写法，改一处另一处必然漂移）',
                )

    def test_代码里不许再手写错误code(self):
        for name, src in self.files.items():
            with self.subTest(file=name):
                for code in ('insufficient_balance', 'billing_error'):
                    self.assertNotIn(
                        code, _code_strings(src),
                        f'{name} 里手写了 code={code!r} —— code 与状态码由 billing 给，'
                        f'否则会出现「402 说余额不足、code 说服务端出错」这种自相矛盾的回包',
                    )

    def test_两端点都走同一张翻译表(self):
        for name, src in self.files.items():
            with self.subTest(file=name):
                called = _called_names(src)
                self.assertIn(
                    'deduct_failure_payload', called,
                    f'{name} 的扣费失败没走 billing.deduct_failure_payload —— '
                    f'这正是「服务端出错被回成余额不足」的那个入口',
                )
                # 只断言「调用过」不够：两个端点各有**两处**余额闸门，改掉其中一处、
                # 另一处还留着，上面那条照样绿。所以按闸门数量逐一核对。
                gates = _balance_gate_count(src)
                calls = _call_count(src, 'precheck_failure')
                self.assertGreaterEqual(gates, 1, f'{name} 里找不到入口余额闸门 —— 这条锁需要跟着改')
                self.assertEqual(
                    gates, calls,
                    f'{name} 有 {gates} 处 `balance <= 0` 闸门，却只调了 {calls} 次 '
                    f'billing.precheck_failure —— 少调的那处又在自己写文案了',
                )

    def test_扣费失败按三档判_不是布尔值(self):
        # 旧写法：`if not billing_success`。布尔值只剩「成/败」，败的那一支
        # 只能挑一种说法 —— 挑中的就是「余额不足」。
        #
        # 第 9 轮把两个端点各自那份 `_update_usage_log` 并成了
        # `views_openai.update_usage_log` 一份（usage 解析同时并到
        # `apps/utils/billing.parse_usage*`），所以这条锁跟着改成锁**那一份**：
        # 收尾必须把扣费交给 `charge_usage`，而 `charge_usage` 必须回 (三档, 金额)。
        openai_src = _read(OPENAI_VIEWS)
        code = _strip_strings(_func_body(openai_src, 'update_usage_log'))
        self.assertIn(
            'charge_usage(', code,
            '唯一的收尾实现里不再有 charge_usage —— 扣费逻辑被内联回去了，'
            '两个端点很快又会各长一份',
        )

        charge = _strip_strings(_func_body(openai_src, 'charge_usage'))
        self.assertIn('calculate_and_deduct_cost(', charge, 'charge_usage 没真的去扣费')
        self.assertNotRegex(
            charge, r'return (?:cost|0), (?:True|False)\b',
            '计费结果又退回布尔值了 —— 「余额不足」与「服务端出错」就只剩一种说法',
        )
        self.assertRegex(
            charge, r'return status, cost',
            '应回 (状态, 金额)：调用方要靠金额判断这一笔是不是本该收费',
        )

        # 两个端点都必须调那一份。各留一份复制品的话，上面全绿也拦不住漂移 ——
        # 而漂移的后果是「同一个上游、不同的端点、算出不同的用量」，直接决定收多少钱。
        for name, src in self.files.items():
            with self.subTest(file=name):
                self.assertIn(
                    'update_usage_log', _called_names(src),
                    f'{name} 没走共用的收尾实现（views_openai.update_usage_log）—— '
                    f'两个端点各写一份，usage 解析与 cached_tokens 迟早再漂移一次',
                )

    def test_calculate_and_deduct_cost不再返回布尔值(self):
        body = _func_body(_read(OPENAI_VIEWS), 'calculate_and_deduct_cost')
        code = _strip_strings(body)
        self.assertNotRegex(
            code, r'return (0|cost), (True|False)\b',
            'LLM 扣费又返回布尔值了 —— 调用方会把每条失败都读成「余额不足」',
        )
        self.assertIn('DEDUCT_ERROR', code)
        self.assertIn('DEDUCT_OK', code)

    def test_入口说的话与扣费失败说的话不是同一句(self):
        # 一条是「你真的没充钱」（入口按 balance<=0 判的），
        # 一条是「我们这边出错了」。两者必须由不同函数给出：
        # 两处共用同一句，就会有一边是假话。
        src = _read(OPENAI_VIEWS)
        called = _called_names(src)
        self.assertIn('precheck_failure', called)
        self.assertIn('deduct_failure_payload', called)
        body = _func_body(src, 'calculate_and_deduct_cost')
        self.assertNotIn(
            'precheck_failure', _strip_strings(body),
            '扣费函数里去做入口的余额校验 —— 那条判断属于入口，放进来会让'
            '「余额不足」与「服务端出错」重新混成一档',
        )


if __name__ == '__main__':
    unittest.main()
