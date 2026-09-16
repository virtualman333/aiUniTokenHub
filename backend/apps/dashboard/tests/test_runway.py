"""余额续航预测的单元测试 —— 纯 Python，不需要数据库、不需要 Django settings。

    cd backend && python -m unittest discover -s apps/dashboard/tests -t . -v

这个模块给出的是一句「你的钱还能用几天」，用户会直接照着它决定要不要充值，
所以边界必须钉死：余额为 0、窗口内没消耗、账号刚用两天（窗口被摊薄会导致
续航虚高）这三种情况最容易算错。
"""
import unittest
from datetime import date, timedelta
from decimal import Decimal

from apps.dashboard.runway import estimate_runway

TODAY = date(2026, 9, 16)


def days_back(offsets_and_costs):
    """把「几天前 → 消耗」的映射转成 (日期, 消耗) 列表。"""
    return [(TODAY - timedelta(days=n), c) for n, c in offsets_and_costs]


class TestEstimateRunway(unittest.TestCase):
    def test_没有任何消耗记录_返回_idle(self):
        r = estimate_runway([], 100, today=TODAY)
        self.assertEqual(r["level"], "idle")
        self.assertIsNone(r["runway_days"])
        self.assertEqual(r["balance"], 100)
        self.assertIn("没有产生消耗", r["advice"])

    def test_daily_costs_为_None_不报错(self):
        r = estimate_runway(None, 100, today=TODAY)
        self.assertEqual(r["level"], "idle")

    def test_余额为零_返回_empty(self):
        r = estimate_runway(days_back([(0, 1), (1, 1)]), 0, today=TODAY)
        self.assertEqual(r["level"], "empty")
        self.assertIsNone(r["runway_days"])
        self.assertIn("充值", r["advice"])

    def test_余额为负_同样按_empty_处理(self):
        r = estimate_runway(days_back([(0, 1)]), Decimal("-3.5"), today=TODAY)
        self.assertEqual(r["level"], "empty")

    def test_稳定消耗_满窗口(self):
        # 最近 7 天每天 1 元 → 窗口 7 天，日均 1 元，余额 10 → 还能用 10 天
        r = estimate_runway(days_back([(n, 1) for n in range(7)]), 10, today=TODAY)
        self.assertEqual(r["window_days"], 7)
        self.assertEqual(r["active_days"], 7)
        self.assertEqual(r["avg_daily_cost"], 1)
        self.assertEqual(r["runway_days"], 10)
        self.assertEqual(r["level"], "safe")

    def test_窗口不会超过账户的实际跨度(self):
        # 只有昨天和今天有记录 → 窗口收成 2 天，而不是拿 7 天把日均摊薄
        r = estimate_runway(days_back([(0, 2), (1, 2)]), 10, today=TODAY)
        self.assertEqual(r["window_days"], 2)
        self.assertEqual(r["avg_daily_cost"], 2)
        self.assertEqual(r["runway_days"], 5)

    def test_只用了今天一天_窗口为1(self):
        r = estimate_runway(days_back([(0, 4)]), 8, today=TODAY)
        self.assertEqual(r["window_days"], 1)
        self.assertEqual(r["avg_daily_cost"], 4)
        self.assertEqual(r["runway_days"], 2)
        self.assertIn("今天刚开始消耗", r["advice"])

    def test_零消耗日会摊薄日均_续航更保守(self):
        # 最近 5 天里只有 3 天有消耗，共 3 元 → 窗口 5 天、日均 0.6，余额 3 元只能撑 5 天。
        # 若只按「有消耗的天」算（日均 1 元）会得出 3 天，那是偏乐观的口径；
        # 中间空着的两天同样不该被当成「这两天没在花钱、所以钱更经用」。
        costs = days_back([(0, 1), (2, 1), (4, 1)])
        r = estimate_runway(costs, 3, today=TODAY)
        self.assertEqual(r["window_days"], 5)
        self.assertEqual(r["active_days"], 3)
        self.assertAlmostEqual(r["avg_daily_cost"], 0.6, places=6)
        self.assertEqual(r["runway_days"], 5)

    def test_分级临界值(self):
        # 日均 1 元，用余额控制续航天数，逐个卡在分级边界上
        costs = days_back([(n, 1) for n in range(7)])
        self.assertEqual(estimate_runway(costs, 1, today=TODAY)["level"], "critical")
        self.assertEqual(estimate_runway(costs, 3, today=TODAY)["level"], "critical")
        self.assertEqual(estimate_runway(costs, 4, today=TODAY)["level"], "watch")
        self.assertEqual(estimate_runway(costs, 7, today=TODAY)["level"], "watch")
        self.assertEqual(estimate_runway(costs, 8, today=TODAY)["level"], "safe")

    def test_续航按天向上取整(self):
        # 余额 1.5 / 日均 1 → 1.5 天，向上取整成 2 天（不够一天也算一天）
        r = estimate_runway(days_back([(n, 1) for n in range(7)]), Decimal("1.5"), today=TODAY)
        self.assertEqual(r["runway_days"], 2)

    def test_耗尽日期等于今天加续航天数(self):
        r = estimate_runway(days_back([(n, 1) for n in range(7)]), 10, today=TODAY)
        self.assertEqual(r["exhaust_date"], (TODAY + timedelta(days=10)).isoformat())

    def test_空窗口_no_balance_时不给耗尽日期(self):
        r = estimate_runway([], 100, today=TODAY)
        self.assertIsNone(r["exhaust_date"])
        r2 = estimate_runway(days_back([(0, 1)]), 0, today=TODAY)
        self.assertIsNone(r2["exhaust_date"])

    def test_输入乱序也算对(self):
        ordered = days_back([(0, 1), (1, 1), (2, 1)])
        shuffled = days_back([(2, 1), (0, 1), (1, 1)])
        self.assertEqual(
            estimate_runway(ordered, 9, today=TODAY),
            estimate_runway(shuffled, 9, today=TODAY),
        )

    def test_未来日期与窗口外的旧记录都被排除(self):
        costs = days_back([(0, 1)]) + [((TODAY + timedelta(days=3)), 999)]
        r = estimate_runway(costs, 5, today=TODAY)
        self.assertEqual(r["window_days"], 1)
        self.assertEqual(r["avg_daily_cost"], 1)
        self.assertEqual(r["runway_days"], 5)

    def test_Decimal_与_float_结果一致(self):
        a = estimate_runway(days_back([(0, Decimal("1.234567"))]), Decimal("10.5"), today=TODAY)
        b = estimate_runway(days_back([(0, 1.234567)]), 10.5, today=TODAY)
        self.assertEqual(a, b)

    def test_返回字段齐全(self):
        r = estimate_runway(days_back([(0, 1)]), 3, today=TODAY)
        for key in ("balance", "window_days", "active_days", "avg_daily_cost",
                    "runway_days", "exhaust_date", "level", "level_text", "advice"):
            self.assertIn(key, r)
        self.assertEqual(r["level_text"], "余额告急")
        self.assertIn("还能用 3 天", r["advice"])

    def test_自定义窗口天数(self):
        r = estimate_runway(days_back([(n, 1) for n in range(30)]), 30, today=TODAY, window_days=30)
        self.assertEqual(r["window_days"], 30)
        self.assertEqual(r["runway_days"], 30)

    def test_无窗口天数为零时不会除零(self):
        r = estimate_runway(days_back([(0, 1)]), 10, today=TODAY, window_days=0)
        self.assertEqual(r["window_days"], 1)
        self.assertEqual(r["avg_daily_cost"], 1)


if __name__ == "__main__":
    unittest.main()
