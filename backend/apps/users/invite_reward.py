# -*- coding: utf-8 -*-
"""邀请返利的判定与金额 —— **纯 Python，不 import Django**（可被 `run_tests.py` 直接测）。

为什么单独一个模块
------------------
`apps/users/utils.py::process_invite_reward` 是全仓唯一**主动给用户加钱**的地方
（被邀请人充值 → 给邀请人返利），而 `apps/users/` 2511 行此前**一条测试都没有** ——
`run_tests.py` 的 `NO_TESTS_YET` 里曾写着「这是下一轮的第一件事」，本模块就是那件事。
做不了的原因不是没时间，是那个函数把三件事揉成了一个：

  1. 该不该发（三种返利方式 × 是否已有记录 × 已批准人数够没够）；
  2. 金额（充值额 × 比例）与分流（≥ 审核阈值走 `pending`，否则立刻打钱）；
  3. 三次 ORM 查询 + 建 `InviteReward` + 改 `User.balance` + 写 `Bill`。

第 3 步要连库（本仓库的测试契约是「不连库」，见 AGENTS.md），而第 1、2 步全是
纯算术与分支。这里把 1、2 抽出来，**查询以惰性取值函数的形式传进来** ——
顺带修掉一处白跑：`rebate_type='every'` 时原来也要查两次库，现在一次都不查
（`apps/users/tests/test_invite_reward.py` 用计数器盯着这件事）。

抽出来时立刻暴露的两个真缺陷
----------------------------
1. **同一笔返利，两条路径到账金额不一样。** 立刻打钱那条用的是**没量化**的
   `充值额 × 比例`：`Decimal('99.99') * Decimal('0.10') == 9.999`。
   写进 `InviteReward.reward_amount`（`decimal_places=2`）时数据库把它收成 `10.00`，
   而 `User.balance` 与 `Bill.amount` 是 **6 位**小数、原样收下 `9.999`；
   后台「审核通过」那条又把 `reward_amount` 读回来再发，发的是 `10.00`。
   同一件事两个数 —— 返利记录上的金额与用户实际到账**差 0.001**，两张表永远对不平。
   现在金额统一量化到 2 位（`ROUND_HALF_UP`），审核阈值也按量化后的金额比：
   「返利达到 100 元需审核」说的应该是用户看得见的那个数。
2. **量化后可能变成 0。** `0.04 × 0.10 == 0.004` → 量化后 `0.00`。原来会照样建一条
   `reward_amount=0.00` 的返利记录（`approved` 那条还会往账单里写一条
   「邀请返利 ¥0.00」）。现在金额为 0 一律不发，账面上不留零元记录。

同一个道理还管着**记录里的充值额**：`InviteReward.recharge_amount` 也只有 2 位，
所以它必须与「算出返利的那个数」是同一个。`RewardDecision.recharge_amount` 就是
为这件事存在的 —— 落库那一侧拿它写记录，于是任何一条返利记录都满足
「`recharge_amount × rebate_ratio` 量化后 == `reward_amount`」，审计时能自己复算。

这个模块只管判定，不碰数据库、不碰锁；落库与加锁在 `apps/users/utils.py`
与 `apps/dashboard/views.py` 里（那两个发钱入口都有 `select_for_update` 的结构锁，
见 `apps/users/tests/test_invite_reward.py` 的最后一节）。
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable

#: `InviteReward.status` 的两个取值（`rejected` 由人工审核产生，不在这里决定）
PENDING = 'pending'
APPROVED = 'approved'

#: 「已经发过 / 正打算发」的状态 —— `first` / `upgrade` 的去重判据用这个集合。
#: `rejected` 不在里面：被人工拒绝过的，下次充值还能重新触发一次。
COUNTED_STATUSES = (PENDING, APPROVED)

#: `InviteConfig.rebate_type` 的三个取值（与 `models.py` 的 `REBATE_TYPE_CHOICES` 对照，
#: 由 `apps/users/tests/test_invite_reward.py` 从模型源码里解析着对齐）
REBATE_FIRST = 'first'
REBATE_EVERY = 'every'
REBATE_UPGRADE = 'upgrade'
KNOWN_REBATE_TYPES = (REBATE_FIRST, REBATE_EVERY, REBATE_UPGRADE)

#: 金额精度 —— **与 `InviteReward.reward_amount` / `recharge_amount` 的
#: `decimal_places=2` 对齐**。这是「记录上的钱」与「到账的钱」必须相等的那条线：
#: 两边各自取精度就会对不平。
AMOUNT_PLACES = Decimal('0.01')


@dataclass(frozen=True)
class RewardDecision:
    """一次返利判定的结果。

    `reason` 是给日志和测试看的：判不判、为什么，落库那一侧不需要它。
    `recharge_amount` 是**记录里那一栏该写的数**（量化到 2 位），不是原样的入参 ——
    见模块 docstring 最后一段。判成「不发」时它与 `amount` 一起归零：没有记录，
    就没有「记录里的充值额」，落库那一侧也就拿不到一个可以被误用的数。
    """
    should_reward: bool
    amount: Decimal
    recharge_amount: Decimal
    status: str
    reason: str


def _no_reward(reason: str) -> RewardDecision:
    return RewardDecision(False, Decimal('0.00'), Decimal('0.00'), '', reason)


def quantize_amount(value) -> Decimal:
    """把金额收成 2 位小数（四舍五入）。

    用 `ROUND_HALF_UP` 而不是 Decimal 的默认 `ROUND_HALF_EVEN`：`0.005` 在
    银行家舍入下会变成 `0.00`，用户看到的是「明明该给 1 分却没给」。
    中文语境里的「四舍五入」就是 HALF_UP，账面上的数也要跟它一致。
    """
    return Decimal(str(value)).quantize(AMOUNT_PLACES, rounding=ROUND_HALF_UP)


def reward_amount(recharge_amount, rebate_ratio) -> Decimal:
    """返利金额 = 充值额 × 返利比例，**量化到 2 位**（记录与账单收的是同一个数）。

    充值额先量化再乘：列宽只有 2 位，记录里的充值额与这里用的充值额必须是同一个数，
    否则「拿记录复算返利」会算出第二个答案。
    """
    recharge = quantize_amount(recharge_amount)
    return quantize_amount(recharge * Decimal(str(rebate_ratio)))


def decide_reward(
    *,
    rebate_type,
    rebate_ratio,
    reward_threshold,
    upgrade_threshold,
    recharge_amount,
    already_rewarded: Callable[[], bool],
    approved_invitees: Callable[[], int],
) -> RewardDecision:
    """该不该发、发多少、走审核还是立刻打钱。

    两个 `Callable` 是**惰性取值函数**，不是值：判定用不到时它们一次都不会被调用
    （`every` 不需要任何查询；金额为 0 时也不需要 —— 原来每次充值都要查两遍库）。
    传函数进来的另一个好处是：落库那一侧可以把它们包在 `select_for_update()` 的
    事务里，判定与写入之间不再有窗口（见 `apps/users/utils.py`）。

    Args:
        rebate_type: `InviteConfig.rebate_type`
        rebate_ratio: `InviteConfig.rebate_ratio`
        reward_threshold: `InviteConfig.reward_threshold`，达到它要走人工审核
        upgrade_threshold: `InviteConfig.upgrade_threshold`，仅 `upgrade` 方式有效
        recharge_amount: 本次充值金额
        already_rewarded: 这对（邀请人, 被邀请人）是否已有 `pending`/`approved` 记录
        approved_invitees: 该邀请人**已审核通过**的去重被邀请人数
    """
    recharge = quantize_amount(recharge_amount)
    amount = reward_amount(recharge, rebate_ratio)
    # 金额为 0 就先退出：比例为 0、充值额为 0、或量化后不足 1 分，都不该建记录。
    # 放在分支之前，是为了让「不算」这条路一次查询都不做。
    if amount <= 0:
        return _no_reward('返利金额为 0，不发')

    should_reward = False
    if rebate_type == REBATE_EVERY:
        should_reward = True
    elif rebate_type == REBATE_FIRST:
        should_reward = not already_rewarded()
    elif rebate_type == REBATE_UPGRADE:
        # 满 X 人之后转成「每次返利」，否则退回「首次返利」的判据
        if approved_invitees() >= upgrade_threshold:
            should_reward = True
        else:
            should_reward = not already_rewarded()
    else:
        # 不认识的配置值：**不发**（宁可漏发也不乱发），但要把这个值说出来，
        # 不然界面上把 rebate_type 配错一个字母，表现是「返利静默停了」。
        return _no_reward('返利方式无法识别：%r' % (rebate_type,))

    if not should_reward:
        return _no_reward('不满足返利条件（%s）' % (rebate_type,))

    threshold = quantize_amount(reward_threshold)
    # 阈值比的是**量化后的金额**：用户看见的是 10.00 这条记录，
    # 「满 100 元需审核」就该拿 10.00 去比，而不是拿它背后的 9.999。
    if amount >= threshold:
        return RewardDecision(True, amount, recharge, PENDING,
                              '金额达到 %s，转人工审核' % threshold)
    return RewardDecision(True, amount, recharge, APPROVED,
                          '金额未达 %s，立即到账' % threshold)
