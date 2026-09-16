# -*- coding: utf-8 -*-
"""`apps/image_gen/billing.py` 的纯函数测试（不需要数据库，也不需要 Django）。

锁的是两件用户能直接看到的事：

1. **「扣费失败」不能一律说成「余额不足」。** 服务端出错时让用户去充值，
   是把他引到一个解决不了任何问题的地方。所以 `DEDUCT_ERROR` 那条文案里
   一个字都不许出现「余额」。
2. **没退到钱就不能说「已退款」。** 退款金额为 0 时（没扣过，或已经退过），
   文案必须换成「本次未产生费用」—— 说了「已退款」，用户会去账单里找那条
   根本不存在的退款记录。

跑法（在 backend/ 下）：python run_tests.py
"""
import unittest
from decimal import Decimal

from apps.image_gen import billing


class DeductResultVocabularyTest(unittest.TestCase):
    """三档结果必须是三个不同的值"""

    def test_三档结果互不相同(self):
        values = [billing.DEDUCT_OK, billing.DEDUCT_INSUFFICIENT, billing.DEDUCT_ERROR]
        self.assertEqual(
            len(set(values)), 3,
            '三档结果出现了重复值 —— 那样「余额不足」与「服务端出错」又会退化成同一句话',
        )

    def test_失败两档走同一张翻译表(self):
        # 调用方只该问 billing，不该自己 if 一长串
        msg_ins, code_ins = billing.deduct_failure(billing.DEDUCT_INSUFFICIENT, 1, 0)
        msg_err, code_err = billing.deduct_failure(billing.DEDUCT_ERROR, 1, 0)
        self.assertEqual(code_ins, 400)
        self.assertEqual(code_err, 500)
        self.assertNotEqual(msg_ins, msg_err)

    def test_服务端出错的文案里不许出现余额二字(self):
        # 这条是本次修复的核心：用户余额明明够，却被告知「余额不足」，
        # 于是去充值 —— 白充，而且真正的问题被 400 掩盖，前端不会重试。
        msg, _ = billing.deduct_failure(billing.DEDUCT_ERROR, Decimal('0.08'), Decimal('100'))
        self.assertNotIn('余额', msg, '服务端故障的提示又把用户引向充值了')
        self.assertIn('未产生', msg, '要说清楚这次没有扣钱，用户才敢重试')

    def test_成功不该被当成失败处理(self):
        # 传 OK 进来是调用方的逻辑错误。静默返回一句错误文案的话，
        # 一次成功的请求会被回成失败 —— 那是最难查的一类 bug，必须直接抛。
        for value in (billing.DEDUCT_OK, '', None, 'whatever'):
            with self.subTest(status=value):
                with self.assertRaises(ValueError):
                    billing.deduct_failure(value, 1, 1)


class FormatAmountTest(unittest.TestCase):
    """金额展示：余额字段是 6 位小数，直接 f-string 会打出 ¥10.000000"""

    def test_余额不再打出六位小数(self):
        self.assertEqual(billing.format_amount(Decimal('10.000000')), '10.00')
        self.assertEqual(billing.format_amount(Decimal('0.000000')), '0.00')

    def test_两位小数保持不变(self):
        self.assertEqual(billing.format_amount(Decimal('0.08')), '0.08')
        self.assertEqual(billing.format_amount(Decimal('1.5')), '1.50')

    def test_小于一分的单价不会被四舍五入成零(self):
        # 后台可以把单张价格配到 0.0005 这种量级；一律保留两位的话
        # 会显示成 ¥0.00，用户会以为这次生成不要钱。
        self.assertEqual(billing.format_amount(Decimal('0.0005')), '0.0005')
        self.assertEqual(billing.format_amount(Decimal('0.001')), '0.001')

    def test_最多四位小数(self):
        self.assertEqual(billing.format_amount(Decimal('0.123456')), '0.1235')

    def test_整数与进位(self):
        self.assertEqual(billing.format_amount(12), '12.00')
        self.assertEqual(billing.format_amount(Decimal('999999.999999')), '1000000.00')

    def test_负数与零(self):
        self.assertEqual(billing.format_amount(Decimal('-3.5')), '-3.50')
        self.assertEqual(billing.format_amount(0), '0.00')

    def test_脏值不抛异常_按零处理(self):
        for value in (None, '', 'abc', float('nan'), float('inf'), object()):
            with self.subTest(value=repr(value)):
                self.assertEqual(billing.format_amount(value), '0.00')


class InsufficientMessageTest(unittest.TestCase):
    """余额不足：需要多少、还剩多少都要写出来"""

    def test_两个金额都带上且格式统一(self):
        msg = billing.insufficient_message(Decimal('0.080000'), Decimal('10.000000'))
        self.assertIn('¥0.08', msg)
        self.assertIn('¥10.00', msg)
        self.assertNotIn('10.000000', msg, '余额又被打回六位小数了')

    def test_余额为零时也能正常显示(self):
        msg = billing.insufficient_message(Decimal('0.08'), Decimal('0'))
        self.assertIn('¥0.00', msg)


class RefundAmountTest(unittest.TestCase):
    """该退多少：非正一律为零（没扣过就没有钱可退）"""

    def test_正数原样返回(self):
        self.assertEqual(billing.refund_amount_of(Decimal('0.08')), Decimal('0.08'))
        self.assertEqual(billing.refund_amount_of('1.5'), Decimal('1.5'))

    def test_零负值与脏值都退零(self):
        for value in (Decimal('0'), 0, None, '', 'abc', Decimal('-1')):
            with self.subTest(value=repr(value)):
                self.assertEqual(billing.refund_amount_of(value), Decimal('0'))

    def test_退款金额是Decimal_不是float(self):
        # 钱一旦变成 float 就会出现 0.08000000000000002 这种账
        self.assertIsInstance(billing.refund_amount_of(0.1), Decimal)


class RefundMessageTest(unittest.TestCase):
    """退款后说的话，必须与「到底退没退」一致"""

    def test_退了钱就说退了(self):
        msg = billing.refund_message(Decimal('0.08'), '图片保存失败')
        self.assertIn('图片保存失败', msg)
        self.assertIn('已退回 ¥0.08', msg)
        self.assertNotIn('未产生费用', msg)

    def test_没退到钱就不许说已退款(self):
        # 幂等退款会走到这里（第二次调用时 cost 已被归零）。
        # 说「已退款」是假话：用户会去账单里找那条不存在的退款记录。
        msg = billing.refund_message(Decimal('0'), '图片保存失败')
        self.assertNotIn('已退回', msg, '没退到钱却说已退款')
        self.assertIn('本次未产生费用', msg)

    def test_默认原因是生成失败(self):
        self.assertIn('生成失败', billing.refund_message(Decimal('1')))


if __name__ == '__main__':
    unittest.main()
