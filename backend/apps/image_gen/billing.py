"""图像生成的扣费结果与「给用户看的话」—— 唯一来源（纯 Python，不 import Django）。

为什么要单独一个模块：

1. **「扣费失败」以前只有一个含义。** `_deduct_cost` 不管是因为余额不足、
   还是因为数据库/记账出错，都返回同一个 `False`，调用方于是统一回一句
   「余额不足」。两件事的后果完全不同：

   - 余额不足：用户自己充值就能解决 —— 说「余额不足」是对的；
   - 服务端出错：用户充值一万次也解决不了，而且真正的问题被伪装成 400
     （客户端错误），前端不会提示异常、也不会重试。用户只会去充钱。

   现在结果分三档，文案与 HTTP 状态码都由这里给，调用方照着回即可。

2. **退款在模型里、在前端都在，后端却一条都没有产生过。** `Bill` 的
   `refund` 类型和用户端账单页的「退款」样式一直都在，只是没有任何代码
   写它。这里给出退款金额的语义（含幂等），`views.py` 负责在
   「钱已经扣了、图没存下来」时真的退回去。

3. 钱的逻辑不能只有连库才测得了 —— MySQL 测试环境起不起得来不由我们说了算
   （见 AGENTS.md「测试不连数据库」），所以文案与金额规则放在这里，
   用 unittest 直接测（`apps/image_gen/tests/test_billing_messages.py`）。

> 如果以后别的应用也要显示金额，把 `format_amount` 挪到 `apps/utils/money.py`
> 去，别在第二个地方再写一份 —— 现在后端各处分别是 `¥{x}` / `{x:.2f}` /
> `{x:.6f}`，同一笔金额在三个页面是三种样子。
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# ============================================================
# 扣费结果
# ============================================================
#
# 三种结果，不是布尔值：「失败」有两种，而它们该对用户说的话完全不同。
#
#: 扣费成功
DEDUCT_OK = 'ok'
#: 余额不足 —— 用户自己充值就能解决，400
DEDUCT_INSUFFICIENT = 'insufficient'
#: 扣费过程出错（数据库/记账/字段异常）—— 平台的问题，用户充钱也没用，500
DEDUCT_ERROR = 'error'

#: 服务端故障时给用户的话。**刻意不提「余额」二字** ——
#: 提了就会把人引去充值，而充值并不能解决任何问题。
DEDUCT_ERROR_MESSAGE = '扣费失败，本次未产生任何费用，请稍后重试'


def to_decimal(value, default: str = '0') -> Decimal:
    """把任意值转成 Decimal。转不了就用 default（默认 0）。

    调用方全是请求处理器，这里只保证「一个脏值不会把整条请求打成 500」，
    值的合法性由序列化器与字段本身负责。
    """
    if isinstance(value, Decimal) and value.is_finite():
        return value
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)
    return result if result.is_finite() else Decimal(default)


def format_amount(value, min_decimals: int = 2, max_decimals: int = 4) -> str:
    """把金额显示成人看的样子：`10.000000` → `10.00`，`0.08` → `0.08`。

    余额字段是 6 位小数，直接 f-string 会打出一句
    「当前余额 ¥10.000000」——用户得自己数小数点后几位。

    规则：**至少 `min_decimals` 位、至多 `max_decimals` 位**。取上限而不是
    一律保留两位，是因为后台可以把单张图片的价格配到 0.0005 这种量级，
    四舍五入成 `0.00` 会让人以为这次生成是免费的。
    """
    amount = to_decimal(value)
    step = Decimal(1).scaleb(-max(0, max_decimals))
    text = f'{amount.quantize(step, rounding=ROUND_HALF_UP):f}'
    if '.' not in text:
        text += '.'
    int_part, frac = text.split('.')
    frac = frac.rstrip('0')
    if len(frac) < min_decimals:
        frac = frac.ljust(min_decimals, '0')
    return f'{int_part}.{frac}' if frac else int_part


# ============================================================
# 给用户看的话
# ============================================================

def insufficient_message(cost, balance) -> str:
    """余额不足。把「需要多少、还有多少」都写出来，用户不用自己去猜。"""
    return (
        f'余额不足，本次需要 ¥{format_amount(cost)}，'
        f'当前余额 ¥{format_amount(balance)}'
    )


def deduct_failure(status: str, cost=0, balance=0):
    """扣费结果 → `(给用户的话, HTTP 状态码)`。

    只处理失败的两档 —— 传 `DEDUCT_OK` 进来是调用方的逻辑错误，直接抛，
    别让「成功」被当成「失败」回给用户（那才是最难查的一类 bug）。
    """
    if status == DEDUCT_INSUFFICIENT:
        return insufficient_message(cost, balance), 400
    if status == DEDUCT_ERROR:
        return DEDUCT_ERROR_MESSAGE, 500
    raise ValueError(
        f'deduct_failure() 只接受失败结果，收到 {status!r}；'
        f'扣费成功不该走这条分支'
    )


def refund_amount_of(cost) -> Decimal:
    """本次该退回多少。

    退款的幂等靠**把 `generation.cost` 归零**实现（两者在同一个事务里完成）：
    所以第二次调用拿到的是 0，退不出第二遍。为此不需要新增字段或迁移 ——
    字段归零本身就是最诚实的记录（这笔生成净收费 0）。

    非正值一律返回 0：没扣过钱，就没有钱可退。
    """
    amount = to_decimal(cost)
    return amount if amount > 0 else Decimal('0')


def refund_message(amount, reason: str = '生成失败') -> str:
    """退款后告诉用户发生了什么。

    ⚠ 金额为 0 时**不能说「已退款」** —— 那是句假话。钱没扣过（或已经退过），
    这时候该说的是「本次未产生费用」。用户按字面理解「已退款」，
    然后去账单里找那条退款记录，只会什么都找不到。
    """
    if refund_amount_of(amount) > 0:
        return f'{reason}，已退回 ¥{format_amount(amount)}，请稍后重试'
    return f'{reason}，本次未产生费用，请稍后重试'
