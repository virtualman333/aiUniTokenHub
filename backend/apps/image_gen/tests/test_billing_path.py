# -*- coding: utf-8 -*-
"""
图片生成扣费路径的「不许回退」锁（纯 Python，不依赖 Django settings 与数据库）

为什么用读源码的方式锁
----------------------
本仓库的单元测试契约是**不连数据库**（见 AGENTS.md）。而这里要锁的事情 ——
「扣费是否在事务与行锁内」「余额不足时图有没有先落库」—— 全都发生在
数据库操作里，靠 unittest 跑不出来。既然跑不出来，就用断言把源码里那几行
关键结构钉住：它们一旦被改回老写法，测试立刻红。

这不是万能锁，它锁的是**结构**而不是**行为**。行为层面的正确性仍然依赖
代码评审 —— 但至少「有人悄悄把行锁删掉」「有人把保存图片挪回扣费之前」
这两种回退不会再无声无息地发生。

跑法（在 backend/ 下，不需要数据库）：
    python run_tests.py
"""
import re
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]

IMAGE_VIEWS = BACKEND / 'apps' / 'image_gen' / 'views.py'
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


if __name__ == '__main__':
    unittest.main()
