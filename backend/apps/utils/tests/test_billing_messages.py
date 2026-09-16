# -*- coding: utf-8 -*-
"""`apps/utils/billing.py` 的纯函数测试（不需要数据库，也不需要 Django）。

锁的是几件用户能直接看到的事：

1. **「扣费失败」不能一律说成「余额不足」。** 服务端出错时让用户去充值，
   是把他引到一个解决不了任何问题的地方。所以 `DEDUCT_ERROR` 那条文案里
   一个字都不许出现「余额」。
2. **没退到钱就不能说「已退款」。** 退款金额为 0 时（没扣过，或已经退过），
   文案必须换成「本次未产生费用」—— 说了「已退款」，用户会去账单里找那条
   根本不存在的退款记录。
3. **同一个意思不许有两种说法。** 图片路径与两个 OpenAI 兼容端点走同一张
   翻译表；`code` 与 HTTP 状态码不能各判一次（改了状态码而漏改 code，
   就会回出「402 + billing_error」这种自相矛盾的东西）。

跑法（在 backend/ 下）：python run_tests.py
"""
import unittest
from decimal import Decimal

from apps.utils import billing


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


class OpenAiBillingPayloadTest(unittest.TestCase):
    """OpenAI 兼容端点的失败回包：message / code / 状态码必须自洽

    这几个端点（`/api/proxy/v1/chat/completions`、`/v1/responses`）此前把
    **服务端扣费出错**回成 402 + `insufficient_balance` + 「余额不足，请充值
    后再试。」—— 用户余额明明够，却被引去充值；客户端看到 402 也不会重试，
    而它其实是一次平台故障。
    """

    def test_服务端出错走500且不借余额不足的code(self):
        msg, code, http_status = billing.deduct_failure_payload(billing.DEDUCT_ERROR, Decimal('0.5'), Decimal('100'))
        self.assertEqual(http_status, 500, '服务端故障回成 4xx，客户端会当成自己的错、不重试')
        self.assertEqual(code, billing.CODE_BILLING_ERROR)
        self.assertNotEqual(code, billing.CODE_INSUFFICIENT, '又借了余额不足的 code —— 客户端会弹「去充值」')
        self.assertNotIn('余额', msg, '服务端故障的提示又把用户引向充值了')

    def test_余额不足走402(self):
        msg, code, http_status = billing.deduct_failure_payload(billing.DEDUCT_INSUFFICIENT, Decimal('0.5'), Decimal('0'))
        self.assertEqual(http_status, billing.INSUFFICIENT_HTTP_STATUS)
        self.assertEqual(code, billing.CODE_INSUFFICIENT)
        self.assertIn('余额', msg)

    def test_余额不足的文案两条路径是同一句(self):
        # 图片路径与 OpenAI 兼容端点：同一个意思，同一句话。
        # 文件里的字面量只该有一份（在 insufficient_message 里）。
        msg_image, _http_image = billing.deduct_failure(billing.DEDUCT_INSUFFICIENT, Decimal('0.5'), Decimal('0'))
        msg_chat, _code_chat, _http_chat = billing.deduct_failure_payload(
            billing.DEDUCT_INSUFFICIENT, Decimal('0.5'), Decimal('0'))
        self.assertEqual(msg_image, msg_chat)

    def test_两条路径的状态码差异是有意的且写在纸上(self):
        # 图片路径余额不足回 400（它的既有契约），OpenAI 兼容端点回 402。
        # 这个差异是可以的，**但必须是决定而不是巧合** —— 所以把它钉住：
        # 谁哪天顺手改了一边，这条就红，然后他得先想清楚为什么两边不同。
        _msg, http_image = billing.deduct_failure(billing.DEDUCT_INSUFFICIENT)
        _msg2, _code, http_chat = billing.deduct_failure_payload(billing.DEDUCT_INSUFFICIENT)
        self.assertEqual(http_image, 400, '图片路径的 400 被改了 —— 图片前端的错误分支要跟着查')
        self.assertEqual(http_chat, 402)
        self.assertEqual(http_chat, billing.INSUFFICIENT_HTTP_STATUS)

    def test_服务端出错两档都不许用余额不足的说法(self):
        # 两档的文案必须不同，且服务端那档不许出现「余额」
        _ins, _c1, status_ins = billing.deduct_failure_payload(billing.DEDUCT_INSUFFICIENT)
        msg_err, _c2, status_err = billing.deduct_failure_payload(billing.DEDUCT_ERROR)
        self.assertNotEqual(status_ins, status_err)
        self.assertNotIn('余额', msg_err)

    def test_payload也不许接受成功(self):
        for value in (billing.DEDUCT_OK, '', None):
            with self.subTest(status=value):
                with self.assertRaises(ValueError):
                    billing.deduct_failure_payload(value)
                with self.assertRaises(ValueError):
                    billing.deduct_failure_code(value)

    def test_错误信封只有一个形状(self):
        payload = billing.openai_error('x', 'y')
        self.assertEqual(set(payload), {'error'})
        self.assertEqual(set(payload['error']), {'message', 'type', 'code'})
        self.assertEqual(payload['error']['type'], billing.CHAT_ERROR_TYPE)
        self.assertEqual(payload['error']['message'], 'x')
        self.assertEqual(payload['error']['code'], 'y')


class PrecheckFailureTest(unittest.TestCase):
    """入口前置校验：这里说「余额不足」是**事实**，不是猜测"""

    def test_说的是余额不足并带上当前余额(self):
        msg, code, http_status = billing.precheck_failure(Decimal('0'))
        self.assertEqual(code, billing.CODE_INSUFFICIENT)
        self.assertEqual(http_status, 402)
        self.assertIn('余额不足', msg)
        self.assertIn('¥0.00', msg, '只说了句余额不足，用户还得自己去看差多少')

    def test_透支的余额如实显示负数(self):
        # 两条扣费路径都允许把余额扣成负数（已消耗的上游成本必须记账），
        # 所以「余额 -1.23」是真实存在的状态，不能被格式化成 0 或漏掉负号
        msg, _code, _http = billing.precheck_failure(Decimal('-1.230000'))
        self.assertIn('¥-1.23', msg)

    def test_前置校验与后置扣费不共用一句话(self):
        # 前置：按 balance<=0 判断，说「余额不足」是对的；
        # 后置扣费失败：只可能是服务端出错，绝不能说余额不足。
        pre_msg, _c, _h = billing.precheck_failure(Decimal('0'))
        err_msg, _c2, _h2 = billing.deduct_failure_payload(billing.DEDUCT_ERROR)
        self.assertNotEqual(pre_msg, err_msg)


if __name__ == '__main__':
    unittest.main()
