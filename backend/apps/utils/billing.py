"""扣费结果与「给用户看的话」—— **全平台唯一来源**（纯 Python，不 import Django）。

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
   写它。这里给出退款金额的语义（含幂等），`image_gen/views.py` 负责在
   「钱已经扣了、图没存下来」时真的退回去。

3. 钱的逻辑不能只有连库才测得了 —— MySQL 测试环境起不起得来不由我们说了算
   （见 AGENTS.md「测试不连数据库」），所以文案与金额规则放在这里，
   用 unittest 直接测（`apps/utils/tests/test_billing_messages.py`）。

4. **它不只服务图片生成。** 这个模块原先长在 `apps/image_gen/` 下，因为当时
   只有图片路径分了档；而两个 OpenAI 兼容端点
   （`api_proxy.views_openai` / `api_proxy.views_responses`）仍在各自手写
   `'余额不足，请充值后再试。'`，并且把**服务端扣费出错**也回成同一句话 ——
   `calculate_and_deduct_cost` 返回布尔值，而它返回 `False` 的三条路径里
   （模型查不到、查模型时抛异常、写余额/记账时抛异常）**没有一条是余额不足**。
   同一个意思在两处各写一份，改了一处另一处就会留下旧说法。现在两条路径共用
   这张翻译表，`openai_*` 那几个函数是给 OpenAI 兼容端点用的出口。

   > 模块原来的 docstring 写着「以后别的应用也要显示金额，把 `format_amount`
   > 挪到 `apps/utils/` 去，别在第二个地方再写一份」—— 这次就是那次搬家。
   > 后端各处仍是 `¥{x}` / `{x:.2f}` / `{x:.6f}` 三种写法，同一笔金额在不同
   > 页面显示成三个样子；收敛它们不在本轮范围内，但**新代码一律走
   > `format_amount`**。
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import NamedTuple, Optional

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

# ============================================================
# OpenAI 兼容端点的错误信封（同样只有一处）
# ============================================================
#
# `type` / `code` 会被客户端拿去分支：有的客户端看到 `insufficient_balance`
# 才弹「去充值」，看到 5xx 才会重试。所以「服务端扣费出错」**绝不能**借
# `insufficient_balance` 这个 code —— 借了，客户端就会把它当成「用户该充钱了」，
# 而那笔请求其实是平台自己的故障。这正是 LLM 路径此前的问题：
# 402 + `insufficient_balance` + 「余额不足，请充值后再试。」
CHAT_ERROR_TYPE = 'billing_error'
CODE_INSUFFICIENT = 'insufficient_balance'
CODE_BILLING_ERROR = 'billing_error'

#: 余额不足的 HTTP 状态码。
#:
#: 图片路径用的是 400（`insufficient_message` + `APIResponse.error` 那一族），
#: OpenAI 兼容端点用的是 402 Payment Required。这是两条端点各自的既有契约，
#: 本轮**不强行统一**（改它要动图片前端的错误分支，收益却为零）；要统一的是
#: 「同一个端点内部」的说法一致 —— 以及下面这条：失败的两档绝不能共用一句话。
INSUFFICIENT_HTTP_STATUS = 402


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


def deduct_failure_code(status: str) -> str:
    """扣费失败 → 错误信封里的 `code`（OpenAI 兼容端点用）。"""
    if status == DEDUCT_INSUFFICIENT:
        return CODE_INSUFFICIENT
    if status == DEDUCT_ERROR:
        return CODE_BILLING_ERROR
    raise ValueError(
        f'deduct_failure_code() 只接受失败结果，收到 {status!r}；'
        f'扣费成功不该走这条分支'
    )


#: OpenAI 兼容端点的失败档 → `(code, HTTP 状态码)`。
#:
#: 为什么不直接用 `deduct_failure` 的状态码：**余额不足那一档两条路径不同**。
#: 图片路径历史上是 400（`APIResponse.error` 那一族），OpenAI 兼容端点是 402
#: Payment Required（与它自己入口的前置校验同值）。改图片那个 400 会动到图片
#: 前端的错误分支，收益为零，所以本轮维持原状 —— 但差异必须写在纸上、由测试
#: 钉住，而不是留在两个人的记忆里。
_OPENAI_FAILURE_CODES = {
    DEDUCT_INSUFFICIENT: (CODE_INSUFFICIENT, INSUFFICIENT_HTTP_STATUS),
    DEDUCT_ERROR: (CODE_BILLING_ERROR, 500),
}


def deduct_failure_payload(status: str, cost=0, balance=0):
    """OpenAI 兼容端点的扣费失败回包内容：`(message, code, http_status)`。

    **文案**与图片路径同一份（`deduct_failure`）—— 同一个意思不该有两种说法。
    分开的只有 `code` 与状态码那一张表，理由见 `_OPENAI_FAILURE_CODES`。

    实际只可能收到 `DEDUCT_ERROR`（余额不足在扣费这一步不可能发生，见
    `precheck_failure` 的说明）；`DEDUCT_INSUFFICIENT` 仍然照常翻译，因为将来
    若有人真的在扣费事务里加上余额判断，那时需要的正是这句话，而不是一个 500。
    """
    if status not in _OPENAI_FAILURE_CODES:
        raise ValueError(
            f'deduct_failure_payload() 只接受失败结果，收到 {status!r}；'
            f'扣费成功不该走这条分支'
        )
    code, http_status = _OPENAI_FAILURE_CODES[status]
    message, _ignored = deduct_failure(status, cost, balance)
    return message, code, http_status


def precheck_failure(balance):
    """入口**前置**余额校验没过 → `(message, code, http_status)`。

    这是唯一一处真的可以说「余额不足」的地方：它按 `balance <= 0` 判断，
    是事实而不是猜测。

    与 `deduct_failure(DEDUCT_INSUFFICIENT)` 的区别值得写下来：扣费那一步
    根本不会因为余额不足而失败 —— 那两条路径（`image_gen._deduct_cost` 与
    `api_proxy.calculate_and_deduct_cost`）都**允许把余额扣成负数**，好让已经
    消耗了上游成本的那一笔请求照样记账，透支由下一次请求的前置校验拦住。
    所以扣费失败只可能是服务端出错，报「余额不足」一定是把用户引错了地方。

    金额也一起写出来：只说了句「余额不足」，用户还得自己去账单页看差多少。
    """
    return (
        f'余额不足，当前余额 ¥{format_amount(balance)}，请充值后再试',
        CODE_INSUFFICIENT,
        INSUFFICIENT_HTTP_STATUS,
    )


def openai_error(message: str, code: str, err_type: str = CHAT_ERROR_TYPE) -> dict:
    """OpenAI 兼容端点的错误信封。

    形状（`{'error': {'message', 'type', 'code'}}`）在计费这几处是同一种，
    所以由这里给；其余几十处非计费错误仍各自内联，收敛它们不在本轮范围。
    """
    return {'error': {'message': message, 'type': err_type, 'code': code}}


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


# ============================================================
# 流式收尾：这笔到底收没收到钱
# ============================================================

def unbilled_stream_note(endpoint: str, upstream_status, total_tokens,
                         user_id=None, usage_log_id=None) -> Optional[str]:
    """成功收尾的流式请求、上游却没给 token 用量 → 返回该记 WARNING 的一句话。

    这是「**这笔没收钱**」的判据，而且只有这一处：两条流式端点
    （`views_openai` 的 `/chat/completions`、`views_responses` 的 `/responses`）
    各自收尾，判据再各写一份必然漂移 —— 而漂移的方向恰好是「一边告警一边沉默」。

    为什么要专门说一句：

      收尾计费写的是 `if total_tokens > 0`。上游没给 usage 时 `total_tokens`
      就是 0，扣费**整段被跳过**：余额一动不动、`UsageLog` 三个 token 字段全 0、
      账单里没有这一笔。而这并不是异常，是正常收尾 —— 不报错、不重试、
      界面上看不出任何区别，与「这次调用真的免费」一模一样。
      唯一能留下痕迹的地方只有日志。

    正常情况它不该被触发：流式请求体现在会主动带
    `stream_options.include_usage`（见 `api_proxy/adapters/upstream_body.py`），
    上游会把 usage 补在流末尾。这句话一旦出现在日志里，说明上游没照做，或者流
    被中途掐断了 —— 那时要么换上游、要么补一个计费兜底，总之得有人知道。

    判定用 `0 < upstream_status < 400`：4xx/5xx 本来就不计费，那是另一回事，
    混进来会让每来一次上游报错就刷一条「没收钱」，很快没人再看它。
    """
    try:
        if int(total_tokens or 0) > 0:
            return None
        status = int(upstream_status or 0)
    except (TypeError, ValueError):
        return None
    if not 0 < status < 400:
        return None

    where = f'user_id={user_id}' if user_id is not None else 'user_id=?'
    if usage_log_id is not None:
        where += f' usage_log={usage_log_id}'
    return (
        f'[Billing] {endpoint} 流式请求已成功（HTTP {status}）但上游没返回 token 用量：'
        f'本次未计费（余额未扣、用量记为 0）。{where}。'
        f'确认请求带上了 stream_options.include_usage，以及上游有没有吞掉它。'
    )


# ============================================================
# 上游用量解析：token 三件套 + 缓存命中
# ============================================================
#
# 「从上游返回体里读出用了多少 token」曾经在**三处**各写一份：
# `views_openai._update_usage_log`、`views_responses._update_usage_log`、
# `views_responses._finalize_stream`。三份的差异不在风格而在**认得的字段**：
# 只有一份认 Responses API 的 `input_tokens`，只有流式那份认
# `cache_read_input_tokens`。于是同一个上游、同一个请求，走不同端点可能
# 算出不同的用量 —— 而这直接决定收多少钱（缓存命中的 input 按折扣单价计费）。
#
# 现在只有这一份：调用方拿到 `usage` 字典也好、整个返回体也好，都从这儿过。

class TokenUsage(NamedTuple):
    """一次上游调用实际消耗的用量（四个值口径统一为「非负整数」）。

    `cached_tokens` 不只是展示用的统计 —— 它参与计费：命中缓存的 input token
    按折扣单价算（见 `api_proxy.calculate_and_deduct_cost` 的 `cached_tokens`
    参数）。漏读它 = 按全价收，用户看不见、对账时也对不出来。
    """

    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_tokens: int


def _as_int(value) -> int:
    """上游的数值字段转非负整数 —— `null` / `'12'` / 负数 / 乱码都不抛。

    为什么不抛：这些字段来自第三方响应体，一个脏值不该把整条请求打成 500
    （调用方没有 try/except，抛出去就是 500 + 用户看到一个平台故障）。
    负数按 0 处理 —— `-1` 是某些代理表示「用量未知」的约定，真的当负数用会
    让 `total_tokens > 0` 这类判断出现莫名其妙的结果。
    """
    try:
        n = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return n if n > 0 else 0


def parse_usage_dict(raw) -> TokenUsage:
    """解析**usage 字典本身**（不含外层 `usage` 键）。

    上游有三种形态，字段名互不重叠，所以可以按指纹直接判：

      - Responses API：`input_tokens` / `output_tokens` / `total_tokens`，
        缓存明细在 `input_tokens_details.cached_tokens`
      - OpenAI / 兼容格式：`prompt_tokens` / `completion_tokens` / `total_tokens`，
        缓存明细在 `prompt_tokens_details.cached_tokens`
      - Anthropic：缓存用 `cache_read_input_tokens`（没有 details 那一层）

    先用 `input_tokens is not None` 判 Responses 形态：这两种形态的字段名没有
    交集，不会互相误判；而且**不能用真值判断**（`in` 或 `or`）—— `input_tokens=0`
    是合法值，用真值判会把一个正经的 Responses 响应当成 OpenAI 形态，于是三个
    字段全读成 0。
    """
    if not isinstance(raw, dict):
        return TokenUsage(0, 0, 0, 0)

    if raw.get('input_tokens') is not None:
        itd = raw.get('input_tokens_details') or {}
        return TokenUsage(
            _as_int(raw.get('input_tokens')),
            _as_int(raw.get('output_tokens')),
            _as_int(raw.get('total_tokens')),
            _as_int(itd.get('cached_tokens')) if isinstance(itd, dict) else 0,
        )

    ptd = raw.get('prompt_tokens_details') or {}
    cached = _as_int(ptd.get('cached_tokens')) if isinstance(ptd, dict) else 0
    # Anthropic 只有 cache_read_input_tokens。两者都可能有值（代理会把 Anthropic
    # 的字段顺手补进 OpenAI 形态），取先有值的那个。
    if not cached:
        cached = _as_int(raw.get('cache_read_input_tokens'))
    return TokenUsage(
        _as_int(raw.get('prompt_tokens')),
        _as_int(raw.get('completion_tokens')),
        _as_int(raw.get('total_tokens')),
        cached,
    )


def parse_usage(response_data) -> TokenUsage:
    """从**完整上游返回体**里解析用量（取 `response_data['usage']`）。

    返回体不是 dict（错误分支收到字符串、None）时给全 0 —— 与「上游确实没回
    usage」是同一个结果，调用方按同一条路走即可（该告警由
    `unbilled_stream_note` 负责）。
    """
    if not isinstance(response_data, dict):
        return TokenUsage(0, 0, 0, 0)
    return parse_usage_dict(response_data.get('usage'))
