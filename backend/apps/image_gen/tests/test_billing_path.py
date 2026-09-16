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
IMAGE_BILLING = BACKEND / 'apps' / 'image_gen' / 'billing.py'
IMAGE_PRICING = BACKEND / 'apps' / 'image_gen' / 'pricing.py'
OPENAI_VIEWS = BACKEND / 'apps' / 'api_proxy' / 'views_openai.py'


def _read(path: Path) -> str:
    assert path.exists(), f'读不到 {path} —— 文件被挪走了？这条锁需要跟着改'
    return path.read_text(encoding='utf-8')


def _func_body(src: str, name: str) -> str:
    """抠出顶层函数体：从 `def name(` 到下一个顶层 def/class。"""
    m = re.search(rf'^def {name}\(', src, re.M)
    assert m, f'找不到顶层函数 {name} —— 改名了？这条锁需要跟着改'
    nxt = re.search(r'^(?:def |class )', src[m.end():], re.M)
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


def _relative_imports(src: str, module: str) -> set:
    """取出 `from .<module> import a, b` 里的所有名字（只认相对导入的一层）。

    注意 AST 里 `from .billing import x` 的 `node.module` 是 `'billing'`，
    点号另外记在 `node.level` 里 —— 所以这里要把调用方传进来的 `'.billing'`
    去掉开头的点再比。比错了不会报错，只会得到空集合（调用方那条
    「一个都没解析到」的断言就是专门拦这个的）。
    """
    wanted = module.lstrip('.')
    found = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module == wanted:
            found.update(alias.name for alias in node.names)
    return found


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
    """views.py 从纯模块 import 的名字必须真的存在

    为什么需要这一条
    ----------------
    本仓库的单元测试不装 Django（`python run_tests.py` 起不来库，也 import 不了
    任何含 `models` 的模块）。于是 `views.py` 顶部的 `from .billing import (...)`
    写错一个名字，**在这个环境里没有任何测试会发现** —— 而线上是每一次图片请求
    都 500。这是纯文本断言补不上的一层：文本测试只能看见那行字，看不见那个名字
    到底存不存在。

    好在 `billing.py` 与 `pricing.py` 是纯 Python（把它们拆出来本来就有这个意义），
    可以真的加载进来、按名字核对。带 Django 的模块（`.models` 等）这里不碰。
    """

    def _assert_names_exist(self, module: str, path) -> None:
        imported = _relative_imports(_read(IMAGE_VIEWS), module)
        self.assertTrue(
            imported,
            f'没从 {module} 解析到任何 import —— AST 或 import 写法变了？这条锁需要跟着改',
        )
        target = _load_pure_module(path)
        for name in sorted(imported):
            with self.subTest(module=module, name=name):
                self.assertTrue(
                    hasattr(target, name),
                    f'views.py 从 {module} 导入了不存在的名字 {name} —— '
                    f'纯文本测试看不见这个，线上会直接 500',
                )

    def test_从billing导入的名字都存在(self):
        self._assert_names_exist('.billing', IMAGE_BILLING)

    def test_从pricing导入的名字也存在(self):
        self._assert_names_exist('.pricing', IMAGE_PRICING)


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
            line.strip() for line in _read(IMAGE_BILLING).splitlines()
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


if __name__ == '__main__':
    unittest.main()
