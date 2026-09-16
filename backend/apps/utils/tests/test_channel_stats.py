# -*- coding: utf-8 -*-
"""上游账号调用统计口径的测试（纯函数，不连数据库）。

锁的是「上游账号管理」页上那两个数字：**调用次数**与**成功率**。

修复前的形态是一整条断链：

  1. `UpstreamAccount`（账号）上**没有** usage_count / error_count / last_used
     这三个字段 —— 它们定义在 `ModelUpstreamAccount`（模型-账号绑定）上；
  2. 但热路径记统计的函数 `update_upstream_usage()` 拿的是**账号**，
     里面用 `if not hasattr(account, 'usage_count'): return` 兜住，于是
     22 个调用点**每一次都是空操作**：看起来在记，其实一条都没记过；
  3. 管理页把这个从未被写过的统计摆了出来，于是永远显示
     「调用次数 0 / 成功率 0.0%」—— 而汇总卡片算的是 `c.success_rate || 100`，
     同一页上两个数字互相矛盾（0.0% vs 100.0%），且都不是真的。

所以这一层要钉两件事：**分母是 usage 而不是 usage+error**，
以及 **usage=0 时是「没调用过」而不是「全失败」**。

跑法（在 backend/ 下）：python run_tests.py
"""
import unittest

from apps.utils.channel_stats import as_count, success_rate, usage_delta


class 成功率的边界Test(unittest.TestCase):
    def test_没有调用过是100不是0(self):
        # 新加的账号要显示 100%：把它显示成 0% 等于告诉管理员「这个账号全挂了」
        self.assertEqual(success_rate(0, 0), 100.0)

    def test_全成功(self):
        self.assertEqual(success_rate(10, 0), 100.0)

    def test_全失败(self):
        self.assertEqual(success_rate(10, 10), 0.0)

    def test_一半(self):
        self.assertEqual(success_rate(10, 5), 50.0)

    def test_分母是用量不是用量加错误(self):
        # 失败那一次**也**计入 usage，所以分母是 10 不是 15。
        # 写成 usage+error 的话这里会得到 33.3 —— 整体偏低且毫无道理。
        self.assertEqual(success_rate(10, 5), 50.0)
        self.assertNotEqual(success_rate(10, 5), round(5 * 100.0 / 15, 1))

    def test_错误数超过用量时夹到0(self):
        # 历史脏数据（比如绑定被改过）不该让成功率变负数
        self.assertEqual(success_rate(3, 99), 0.0)

    def test_保留一位小数(self):
        self.assertEqual(success_rate(3, 1), 66.7)
        self.assertEqual(success_rate(7, 1), 85.7)


class 脏值Test(unittest.TestCase):
    def test_None与空串归零(self):
        self.assertEqual(as_count(None), 0)
        self.assertEqual(as_count(''), 0)

    def test_字符串数字认得(self):
        # 数据库聚合有时给 Decimal / 字符串
        self.assertEqual(as_count('42'), 42)

    def test_负数归零(self):
        self.assertEqual(as_count(-5), 0)

    def test_布尔不算次数(self):
        # True/False 是 bool，别被 int() 吃成 1/0 —— 那是「有没有」不是「多少次」
        self.assertEqual(as_count(True), 0)

    def test_浮点截断不抛(self):
        self.assertEqual(as_count(3.9), 3)

    def test_垃圾值不抛(self):
        # 一个脏值不该让整个账号列表接口 500
        self.assertEqual(as_count('abc'), 0)
        self.assertEqual(as_count(object()), 0)

    def test_脏值喂进成功率也不抛(self):
        self.assertEqual(success_rate(None, None), 100.0)
        self.assertEqual(success_rate('abc', 'abc'), 100.0)


class 写入增量Test(unittest.TestCase):
    def test_成功只加用量(self):
        self.assertEqual(usage_delta(True), (1, 0))

    def test_失败用量与错误都加(self):
        self.assertEqual(usage_delta(False), (1, 1))

    def test_增量与成功率自洽(self):
        # 写入侧加出来的 (usage, error) 喂回读取侧，结果必须对得上 ——
        # 两边各写一套口径就是这一层要防的事
        usage = errors = 0
        for ok in (True, True, False, True):
            du, de = usage_delta(ok)
            usage += du
            errors += de
        self.assertEqual((usage, errors), (4, 1))
        self.assertEqual(success_rate(usage, errors), 75.0)
