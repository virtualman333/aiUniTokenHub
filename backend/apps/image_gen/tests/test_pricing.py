# -*- coding: utf-8 -*-
"""
图像生成定价规则单元测试（纯 Python，不依赖 Django settings 与数据库）

为什么测这一层
--------------
`apps/image_gen/pricing.py` 是「一张图卖多少钱」的唯一来源，而这条规则以前在
`views.py` 里写了两遍：

    unit_price = model.per_image_price if model and model.per_image_price else Decimal('0.08')
    total_cost = unit_price * n        # 前置余额校验：决定「拦不拦这次请求」
    ...
    cost = unit_price * n              # 真正扣费：决定「扣多少钱」

两处漂移的后果不是显示错误：按 A 价拦、按 B 价扣，用户会看到「余额不足」而余额
明明够；反过来则把余额扣穿。兜底常量 `0.08` 也各写一份，改一处漏一处。

这里锁住的核心是一条容易被"好心"改坏的语义：**`per_image_price = 0` 表示没配，
不表示免费**（字段 default 就是 0）。谁要是把兜底值调成 0 或把 `> 0` 判断去掉，
未配单价的模型就会变成免费出图 —— 下面第一条断言就会红。

跑法（在 backend/ 下，不需要数据库）：
    python run_tests.py
"""
import unittest
from decimal import Decimal
from types import SimpleNamespace

from apps.image_gen.pricing import (
    DEFAULT_PER_IMAGE_PRICE,
    image_cost,
    unit_price_of,
)


def model_with(price):
    """构造一个只有 per_image_price 的模型替身（不碰数据库）"""
    return SimpleNamespace(per_image_price=price)


class UnitPriceTest(unittest.TestCase):
    """单张价格：配置优先，没配才用兜底"""

    def test_兜底常量必须大于0(self):
        # 把它改成 0 = 所有未配单价的模型免费出图，平台白付上游成本
        self.assertGreater(DEFAULT_PER_IMAGE_PRICE, 0)

    def test_配了单价就用配置值(self):
        self.assertEqual(unit_price_of(model_with(Decimal('0.25'))), Decimal('0.25'))

    def test_单价为0视为没配置_用兜底而不是免费(self):
        self.assertEqual(unit_price_of(model_with(Decimal('0'))), DEFAULT_PER_IMAGE_PRICE)

    def test_单价为0_整型也走兜底(self):
        self.assertEqual(unit_price_of(model_with(0)), DEFAULT_PER_IMAGE_PRICE)

    def test_负数单价走兜底(self):
        self.assertEqual(unit_price_of(model_with(Decimal('-1'))), DEFAULT_PER_IMAGE_PRICE)

    def test_模型为None走兜底(self):
        self.assertEqual(unit_price_of(None), DEFAULT_PER_IMAGE_PRICE)

    def test_对象没有该属性走兜底(self):
        self.assertEqual(unit_price_of(object()), DEFAULT_PER_IMAGE_PRICE)

    def test_脏值不抛异常_一律兜底(self):
        for bad in ('abc', '', [], {}, None):
            with self.subTest(bad=bad):
                self.assertEqual(unit_price_of(model_with(bad)), DEFAULT_PER_IMAGE_PRICE)

    def test_浮点单价不引入二进制误差(self):
        # Decimal(0.08) 是 0.08000000000000000166...，必须走 str() 转换
        got = unit_price_of(model_with(0.08))
        self.assertEqual(got, Decimal('0.08'))
        self.assertEqual(str(got), '0.08')

    def test_字符串单价按十进制解析(self):
        self.assertEqual(unit_price_of(model_with('0.125')), Decimal('0.125'))


class ImageCostTest(unittest.TestCase):
    """总价 = 单价 × 张数，且必须与「单张价格」是同一份规则"""

    def test_单张总价等于单价(self):
        m = model_with(Decimal('0.25'))
        self.assertEqual(image_cost(m, 1), unit_price_of(m))

    def test_按张数相乘(self):
        m = model_with(Decimal('0.25'))
        for n in range(1, 6):
            with self.subTest(n=n):
                self.assertEqual(image_cost(m, n), Decimal('0.25') * n)

    def test_未配单价的模型按兜底价_乘张数(self):
        self.assertEqual(image_cost(model_with(Decimal('0')), 3), DEFAULT_PER_IMAGE_PRICE * 3)

    def test_模型不存在也按兜底价(self):
        self.assertEqual(image_cost(None, 1), DEFAULT_PER_IMAGE_PRICE)

    def test_张数非法一律返回0_不抛异常(self):
        m = model_with(Decimal('0.25'))
        for bad in (0, -1, 'x', None, '', 1.5):
            with self.subTest(bad=bad):
                if bad == 1.5:
                    # int(1.5) == 1：序列化器已限定整数，这里按截断处理即可
                    self.assertEqual(image_cost(m, bad), Decimal('0.25'))
                else:
                    self.assertEqual(image_cost(m, bad), 0)

    def test_返回值始终是Decimal而不是float(self):
        m = model_with(Decimal('0.25'))
        for n in (0, 1, 5):
            with self.subTest(n=n):
                self.assertIsInstance(image_cost(m, n), Decimal)

    def test_总价绝不小于单价_张数合法时(self):
        # 防止把 `* count` 写成别的（比如误改成 `count / 1_000_000` 这类按 token 的算法）
        m = model_with(Decimal('0.25'))
        self.assertGreater(image_cost(m, 5), image_cost(m, 1))


if __name__ == '__main__':
    unittest.main()
