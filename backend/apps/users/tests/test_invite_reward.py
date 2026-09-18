# -*- coding: utf-8 -*-
"""邀请返利的判定（`apps/users/invite_reward.py`）—— 纯 Python，不需要数据库。

`apps/users/` 2511 行此前一条测试都没有，而全仓唯一**主动给用户加钱**的那条线
（被邀请人充值 → 给邀请人返利）就在里面。这套用例钉四件事：

1. **判定矩阵**：三种返利方式 × 有没有记录 × 满没满人 —— 尤其 `every` 不看历史、
   `upgrade` 的 `>=` 边界、以及「不认识的配置值一个都不发」。
2. **钱**：金额与「记录里那一栏」都量化到 2 位、记录自身可复算、量化后为 0 不发，
   并且**阈值比的是量化后的金额** —— 旧实现里 `999.99 × 10%` 算出 `99.999 < 100`，
   「本该送审的」直接打款了。
3. **惰性查询**：判定用不到的查询一次都不发（`every` 零查询、金额为 0 零查询）——
   这是「把查询当取值函数传进来」这件事唯一的可测面。
4. **落库两条入口的锁**（`utils.py::process_invite_reward` /
   `dashboard/views.py::approve_reward`）：加钱那条路的判定必须在
   `select_for_update()` 之内，否则两次充值能各拿一笔返利、两个管理员能点出两份钱。
   这一节先把源码用 `ast.unparse` 剥掉注释再断言（注释不能假装有锁），
   末尾再拿**旧写法**做反向对照 ——「检查跑过了」不等于「检查有判别力」。

最后一节把模块里的常量与 `apps/users/models.py` 的 `choices` / `decimal_places`
对了一遍：真值从模型源码现解析，不经过本模块。
"""
import ast
import dataclasses
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from apps.users.invite_reward import (
    AMOUNT_PLACES,
    APPROVED,
    COUNTED_STATUSES,
    KNOWN_REBATE_TYPES,
    PENDING,
    RewardDecision,
    decide_reward,
    quantize_amount,
    reward_amount,
)

#: backend/ 根 —— tests/ -> users/ -> apps/ -> backend/
BACKEND = Path(__file__).resolve().parents[3]


def decide(**overrides):
    """调 `decide_reward`，把与本节无关的参数填成一份「最普通」的配置。

    入参一律用**字面量**（`'first'` / `'0.10'`），不用模块常量 —— 常量与字面量
    是否一致由最后一节单独钉，混在判定矩阵里会让「矩阵钉的是线上取值」这件事变模糊。
    """
    params = {
        'rebate_type': 'first',
        'rebate_ratio': '0.10',
        'reward_threshold': '100',
        'upgrade_threshold': 10,
        'recharge_amount': '100',
        'already_rewarded': lambda: False,
        'approved_invitees': lambda: 0,
    }
    params.update(overrides)
    return decide_reward(**params)


class TestJudgementMatrix(unittest.TestCase):
    """该不该发 —— 三种返利方式 × 有没有记录 × 满没满人。"""

    # ---- first：只发一次 ----

    def test_first_没有记录就发(self):
        d = decide(rebate_type='first', already_rewarded=lambda: False)
        self.assertTrue(d.should_reward)
        self.assertEqual(d.status, 'approved')
        self.assertEqual(d.amount, Decimal('10.00'))

    def test_first_已有记录不再发(self):
        d = decide(rebate_type='first', already_rewarded=lambda: True)
        self.assertFalse(d.should_reward)
        self.assertIn('first', d.reason)

    def test_first_不看已批准人数(self):
        # 人数门槛只对 upgrade 有意义：first 即使邀请了 100 人，也只发一次
        d = decide(rebate_type='first', already_rewarded=lambda: True,
                   approved_invitees=lambda: 100)
        self.assertFalse(d.should_reward)

    # ---- every：每次都发（包括已经有记录的那次） ----

    def test_every_有记录也发(self):
        d = decide(rebate_type='every', already_rewarded=lambda: True)
        self.assertTrue(d.should_reward)
        self.assertEqual(d.amount, Decimal('10.00'))

    def test_every_没记录也发(self):
        d = decide(rebate_type='every', already_rewarded=lambda: False)
        self.assertTrue(d.should_reward)

    # ---- upgrade：满 X 人后转成 every，否则退回 first ----

    def test_upgrade_人数未满且没有记录_按首次发(self):
        d = decide(rebate_type='upgrade', approved_invitees=lambda: 9,
                   already_rewarded=lambda: False)
        self.assertTrue(d.should_reward)

    def test_upgrade_人数未满且已有记录_不发(self):
        d = decide(rebate_type='upgrade', approved_invitees=lambda: 9,
                   already_rewarded=lambda: True)
        self.assertFalse(d.should_reward)

    def test_upgrade_人数刚好等于门槛_发(self):
        # 边界是 >= 而不是 >：门槛 10 就该在第 10 个人身上生效
        d = decide(rebate_type='upgrade', approved_invitees=lambda: 10,
                   already_rewarded=lambda: True)
        self.assertTrue(d.should_reward)

    def test_upgrade_人数超过门槛_发(self):
        d = decide(rebate_type='upgrade', approved_invitees=lambda: 11,
                   already_rewarded=lambda: True)
        self.assertTrue(d.should_reward)

    # ---- 配置值不认识：一个都不发，但要说出来 ----

    def test_不认识的返利方式_不发且点名那个值(self):
        d = decide(rebate_type='monthly')
        self.assertFalse(d.should_reward)
        self.assertIn('monthly', d.reason)

    def test_返利方式为_None_不发且不抛(self):
        d = decide(rebate_type=None)
        self.assertFalse(d.should_reward)
        self.assertIn('None', d.reason)

    def test_返利方式为空串_不发(self):
        d = decide(rebate_type='')
        self.assertFalse(d.should_reward)

    def test_大小写不同也算不认识(self):
        # choices 里是小写；界面/脚本写错大小写时应当**不发**（宁可漏发也不乱发），
        # 而不是静默按 first 处理
        d = decide(rebate_type='FIRST')
        self.assertFalse(d.should_reward)

    # ---- 不发的时候，返回值本身也要干净 ----

    def test_不发时金额是零且状态为空(self):
        # 落库那一侧拿 decision.amount / decision.status 直接写记录，
        # 「不发」必须表现为「没有金额、没有状态」，不能留个 10.00 让人误用
        for d in (decide(already_rewarded=lambda: True),
                  decide(rebate_type='every', rebate_ratio='0'),
                  decide(rebate_type='monthly')):
            with self.subTest(reason=d.reason):
                self.assertFalse(d.should_reward)
                self.assertEqual(d.amount, Decimal('0.00'))
                self.assertEqual(d.recharge_amount, Decimal('0.00'))
                self.assertEqual(d.status, '')

    def test_每条不发的路都要给出理由(self):
        # 全是静默 return 的话，线上看到的现象只有「返利停了」，查不到为什么
        branches = [
            decide(already_rewarded=lambda: True),
            decide(rebate_type='monthly'),
            decide(rebate_ratio='0'),
            decide(recharge_amount='0'),
        ]
        for d in branches:
            with self.subTest(reason=d.reason):
                self.assertTrue(d.reason.strip(), '不发却没写理由')

    def test_判定结果不可就地修改(self):
        # 落库那一侧不该有「把 decision.amount 改一改再写进去」的余地
        d = decide()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            d.amount = Decimal('999.00')


class TestMoney(unittest.TestCase):
    """发多少钱 —— 量化、复算、零元、阈值。"""

    # ---- 量化到 2 位：记录与到账必须是同一个数 ----

    def test_比例乘出三位小数时按半分向上收(self):
        # 旧实现留下的原样是 9.999：记录列只有 2 位（收成 10.00）、
        # 余额列有 6 位（原样收 9.999），于是同一笔返利出现两个数
        self.assertEqual(reward_amount('99.99', '0.10'), Decimal('10.00'))
        self.assertEqual(reward_amount('99.99', '0.10'),
                         Decimal('9.999').quantize(AMOUNT_PLACES))

    def test_五入而不是银行家舍入(self):
        # 0.01 × 50% = 0.005。Decimal 默认 ROUND_HALF_EVEN 会给 0.00，
        # 用户看到的是「说好给一半，结果一分没给」
        self.assertEqual(reward_amount('0.01', '0.50'), Decimal('0.01'))

    def test_返利金额永远是两位小数(self):
        for recharge, ratio in (('100', '0.1'), ('1', '0.3333'),
                                ('1234.56', '0.07'), ('0.01', '0.5')):
            with self.subTest(recharge=recharge, ratio=ratio):
                value = reward_amount(recharge, ratio)
                self.assertLessEqual(-value.as_tuple().exponent, 2)

    def test_大额不丢精度(self):
        self.assertEqual(reward_amount('12345678.90', '0.1000'),
                         Decimal('1234567.89'))

    def test_比例是四位小数的配置值(self):
        # InviteConfig.rebate_ratio 是 decimal_places=4，默认 0.10
        self.assertEqual(reward_amount('200', '0.1250'), Decimal('25.00'))

    # ---- 记录自身可复算 ----

    def test_记录里的充值额乘比例等于记录里的返利(self):
        """任何一条返利记录都要能被它自己的两个字段复算出来。

        `recharge_amount` 与 `reward_amount` 都是 2 位列；如果返利是按**没量化**的
        充值额算的，审计时拿记录复算就会得到第二个答案。
        """
        samples = (('99.99', '0.10'), ('2.005', '0.50'), ('0.05', '0.20'),
                   ('1234.56', '0.07'), ('10.005', '0.10'))
        for recharge, ratio in samples:
            with self.subTest(recharge=recharge, ratio=ratio):
                d = decide(recharge_amount=recharge, rebate_ratio=ratio,
                           reward_threshold='100000')
                self.assertTrue(d.should_reward, '这组样例本该发钱')
                self.assertEqual(d.recharge_amount,
                                 quantize_amount(recharge),
                                 '记录里的充值额不是 2 位')
                self.assertEqual(
                    quantize_amount(d.recharge_amount * Decimal(ratio)),
                    d.amount,
                    '拿记录里的字段复算，算出来的返利与记录里的不一样',
                )

    def test_不发的时候两个金额都不给数(self):
        """不发就没有记录，也就没有「记录里的充值额」—— 不能留个 0.04 让人误写。

        `0.04 × 10%` 量化后是 0.00：这条充值既没有返利记录、也不该有人拿
        `recharge_amount=0.04` 去建点什么。
        """
        d = decide(recharge_amount='0.04', rebate_ratio='0.10')
        self.assertFalse(d.should_reward)
        self.assertEqual(d.recharge_amount, Decimal('0.00'))
        self.assertEqual(d.amount, Decimal('0.00'))

    # ---- 量化后为 0：不发，也不留零元记录 ----

    def test_量化后不足一分钱不发(self):
        # 0.04 × 10% = 0.004 → 记录列里是 0.00。旧实现只判 `reward <= 0`，
        # 0.004 过得去，于是建一条 0.00 的返利记录、还往余额里加 0.004
        d = decide(recharge_amount='0.04', rebate_ratio='0.10')
        self.assertFalse(d.should_reward)
        self.assertEqual(d.amount, Decimal('0.00'))

    def test_比例为零不发(self):
        self.assertFalse(decide(rebate_ratio='0').should_reward)

    def test_充值额为零不发(self):
        self.assertFalse(decide(recharge_amount='0').should_reward)

    def test_充值额为负不发(self):
        # 绝不能变成「负返利扣钱」
        d = decide(recharge_amount='-100')
        self.assertFalse(d.should_reward)

    def test_刚好一分钱会发(self):
        # 0.05 × 20% = 0.01 —— 边界另一侧：够 1 分就要发
        d = decide(recharge_amount='0.05', rebate_ratio='0.20',
                   reward_threshold='100')
        self.assertTrue(d.should_reward)
        self.assertEqual(d.amount, Decimal('0.01'))

    # ---- 阈值比的是量化后的金额 ----

    def test_阈值比的是用户看得见的那个数(self):
        # 999.99 × 10% = 99.999：按原样比 (< 100) 会**直接打款、绕过审核**；
        # 按记录里那个 100.00 比 (>= 100) 才是「返利满 100 元需审核」的本意
        d = decide(recharge_amount='999.99', rebate_ratio='0.10',
                   reward_threshold='100')
        self.assertEqual(d.amount, Decimal('100.00'))
        self.assertEqual(d.status, 'pending')

    def test_金额等于阈值要走审核(self):
        d = decide(recharge_amount='100', rebate_ratio='0.10',
                   reward_threshold='10')
        self.assertEqual(d.amount, Decimal('10.00'))
        self.assertEqual(d.status, 'pending')

    def test_金额差一分不到阈值就直接到账(self):
        d = decide(recharge_amount='100', rebate_ratio='0.10',
                   reward_threshold='10.01')
        self.assertEqual(d.status, 'approved')

    def test_阈值本身也收成两位(self):
        # 配置里写 99.999 这种数时，两边用同一把尺
        d = decide(recharge_amount='999.99', rebate_ratio='0.10',
                   reward_threshold='99.999')
        self.assertEqual(d.amount, Decimal('100.00'))
        self.assertEqual(d.status, 'pending')

    def test_阈值多出来的零头要先收掉(self):
        # 阈值写 10.004：用户看到的返利是 10.00，按「10.00 够不够 10.00」比应当送审；
        # 拿没量化的 10.004 去比就会判成「没到阈值」直接打款。这一条是给
        # 「阈值也走 quantize_amount」配的判别力证据。
        d = decide(recharge_amount='100', rebate_ratio='0.10',
                   reward_threshold='10.004')
        self.assertEqual(d.amount, Decimal('10.00'))
        self.assertEqual(d.status, 'pending')

    def test_阈值是零时全部走审核(self):
        d = decide(recharge_amount='100', rebate_ratio='0.10',
                   reward_threshold='0')
        self.assertEqual(d.status, 'pending')


class _Counter:
    """惰性取值函数的替身：记下被调用了几次。"""

    def __init__(self, value):
        self.value = value
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.value


class TestLazyQueries(unittest.TestCase):
    """判定用不到的查询，一次都不发。"""

    def test_计数器本身是有效的(self):
        """自证：没有这一条，下面所有「0 次」都可能是「计数根本没接上」。"""
        c = _Counter(True)
        self.assertEqual(c.calls, 0)
        c()
        self.assertEqual(c.calls, 1)

    def test_比例为零时一次都不查(self):
        a, b = _Counter(True), _Counter(0)
        decide(rebate_ratio='0', already_rewarded=a, approved_invitees=b)
        self.assertEqual((a.calls, b.calls), (0, 0))

    def test_充值额为零时一次都不查(self):
        a, b = _Counter(True), _Counter(0)
        decide(recharge_amount='0', already_rewarded=a, approved_invitees=b)
        self.assertEqual((a.calls, b.calls), (0, 0))

    def test_不认识的返利方式一次都不查(self):
        a, b = _Counter(True), _Counter(0)
        decide(rebate_type='monthly', already_rewarded=a, approved_invitees=b)
        self.assertEqual((a.calls, b.calls), (0, 0))

    def test_every_一次都不查(self):
        """每次返利不需要「有没有记录」也不需要「邀请了几个人」。

        旧实现这里照查两遍库 —— 线上最热的充值路径上白跑两次查询。
        """
        a, b = _Counter(True), _Counter(0)
        d = decide(rebate_type='every', already_rewarded=a, approved_invitees=b)
        self.assertTrue(d.should_reward)
        self.assertEqual((a.calls, b.calls), (0, 0))

    def test_first_只查有没有记录(self):
        a, b = _Counter(False), _Counter(0)
        decide(rebate_type='first', already_rewarded=a, approved_invitees=b)
        self.assertEqual((a.calls, b.calls), (1, 0))

    def test_upgrade_达标时不再查有没有记录(self):
        a, b = _Counter(True), _Counter(10)
        d = decide(rebate_type='upgrade', already_rewarded=a, approved_invitees=b)
        self.assertTrue(d.should_reward)
        self.assertEqual((a.calls, b.calls), (0, 1))

    def test_upgrade_未达标时才回落到查记录(self):
        a, b = _Counter(False), _Counter(3)
        decide(rebate_type='upgrade', already_rewarded=a, approved_invitees=b)
        self.assertEqual((a.calls, b.calls), (1, 1))


# ---------------------------------------------------------------------------
# 落库入口的结构锁
# ---------------------------------------------------------------------------

def function_code(path, name):
    """取出某个函数的源码，**剥掉注释与 docstring** 之后重新打印。

    为什么要剥：注释里写一句「这里加了锁」就能骗过 `assertIn('select_for_update')`，
    而那种断言在真正改成「先查后写」之后依然是绿的 —— 假锁。
    `ast.unparse` 只输出语法树上真实存在的东西。
    """
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            body = list(node.body)
            first = body[0] if body else None
            if (isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                body = body[1:]          # 去掉 docstring
            node.body = body
            return ast.unparse(node)
    raise AssertionError('%s 里没有函数 %s' % (path, name))


def audit_process_invite_reward(code):
    """给一段 `process_invite_reward` 的源码，返回它踩的问题（空 = 合格）。"""
    problems = []
    if 'atomic(' not in code:
        problems.append('不在事务里')
    lock = code.find('select_for_update()')
    if lock < 0:
        problems.append('没有加锁 —— 判定与写入之间有窗口')
    if 'User.objects.select_for_update()' not in code:
        problems.append('没有锁邀请人那一行 —— 并发充值会丢一次余额更新')
    decide_at = code.find('decide_reward(')
    if decide_at < 0:
        problems.append('没走 decide_reward（判定可能又抄了一份）')
    for literal in ("'first'", "'every'", "'upgrade'"):
        if literal in code:
            problems.append('自己判了返利方式 %s（第二份判定）' % literal)
    for literal in ("'pending'", "'approved'"):
        if literal in code:
            problems.append('自己抄了状态字面量 %s' % literal)
    if lock >= 0 and decide_at >= 0 and lock > decide_at:
        problems.append('加锁晚于判定 —— 锁没盖住「该不该发」这一步')
    return problems


def audit_approve_reward(code):
    """给一段 `approve_reward` 的源码，返回它踩的问题（空 = 合格）。"""
    problems = []
    if 'atomic(' not in code:
        problems.append('不在事务里')
    lock = code.find('select_for_update()')
    if lock < 0:
        problems.append('没有加锁 —— 两个管理员同时点通过会发两份钱')
    else:
        pending = code.find("status='pending'")
        if pending < 0:
            problems.append('没有确认这一条还是不是 pending')
        elif pending < lock:
            problems.append('先按 pending 查出来再锁 —— 锁盖不住那次读取')
    if 'User.objects.select_for_update()' not in code:
        problems.append('没有锁邀请人那一行 —— 并发审核会丢一次余额更新')
    return problems


class TestMoneyEntryPointsAreLocked(unittest.TestCase):
    """两条加钱的路：判定必须发生在 `select_for_update()` 之内。"""

    def setUp(self):
        self.process = function_code(BACKEND / 'apps' / 'users' / 'utils.py',
                                     'process_invite_reward')
        self.approve = function_code(BACKEND / 'apps' / 'dashboard' / 'views.py',
                                     'approve_reward')

    def test_充值入口的审计结论是干净的(self):
        self.assertEqual(audit_process_invite_reward(self.process), [])

    def test_审核入口的审计结论是干净的(self):
        self.assertEqual(audit_approve_reward(self.approve), [])

    def test_充值入口的查询确实在锁之后(self):
        # 上面那条是「审计函数说我合格」，这条直接看位置，免得审计函数自己被改松
        self.assertLess(self.process.index('select_for_update()'),
                        self.process.index('decide_reward('))

    def test_审核入口的状态确认确实在锁之后(self):
        self.assertLess(self.approve.index('select_for_update()'),
                        self.approve.index("status='pending'"))

    def test_审核入口用的还是记录里那个金额(self):
        # 记录里那个数（2 位）才是到账数 —— 到账另算一遍就是两条路两个数
        self.assertIn('reward.reward_amount', self.approve)

    # ---- 反向对照：这两把「锁的检查」真的会响 ----

    def test_审计函数对旧写法会报红(self):
        """旧 `process_invite_reward`（先查后写、自己判）照抄一遍。

        这一条是给上面两条 `assertEqual(..., [])` 配的**判别力证据**：
        它们绿，不是因为审计函数永远返回空表。
        """
        old = (
            "def process_invite_reward(user, recharge_amount):\n"
            "    inviter = user.invited_by\n"
            "    config = InviteConfig.get_config()\n"
            "    if config.rebate_type == 'first':\n"
            "        should = not InviteReward.objects.filter("
            "inviter=inviter, invitee=user, status__in=['approved', 'pending']).exists()\n"
            "    elif config.rebate_type == 'every':\n"
            "        should = True\n"
            "    if not should:\n"
            "        return\n"
            "    with transaction.atomic():\n"
            "        InviteReward.objects.create(status='approved')\n"
            "        inviter.balance += recharge_amount\n"
            "        inviter.save()\n"
        )
        problems = audit_process_invite_reward(old)
        self.assertTrue(problems, '旧写法竟然判成合格 —— 这个审计函数没有判别力')
        self.assertTrue(any('加锁' in p for p in problems), problems)
        self.assertTrue(any('第二份判定' in p for p in problems), problems)

    def test_审计函数对旧审核写法会报红(self):
        """旧 `approve_reward`：事务外 `get(status='pending')`，事务内改状态加钱。"""
        old = (
            "def approve_reward(self, request, pk=None):\n"
            "    try:\n"
            "        reward = InviteReward.objects.get(pk=pk, status='pending')\n"
            "    except InviteReward.DoesNotExist:\n"
            "        return APIResponse.error('返利记录不存在或已处理', 404)\n"
            "    with models.transaction.atomic():\n"
            "        reward.status = 'approved'\n"
            "        reward.save()\n"
            "        inviter = reward.inviter\n"
            "        inviter.balance += reward.reward_amount\n"
            "        inviter.save()\n"
        )
        problems = audit_approve_reward(old)
        self.assertTrue(problems, '旧写法竟然判成合格 —— 这个审计函数没有判别力')
        self.assertTrue(any('加锁' in p for p in problems), problems)

    def test_注释里写着加了锁也骗不过去(self):
        """注释/docstring 里的字样不算数 —— 源码是剥过注释再看的。

        这条拿一个临时文件真跑一遍 `function_code`：docstring 与注释里都写着
        `select_for_update()`，但函数体里没有 —— 剥不掉就该被审计函数骂。
        """
        fake = (
            "def approve_reward(self, request, pk=None):\n"
            '    """这里 select_for_update() 早就加过了（其实没有）。"""\n'
            "    # select_for_update()\n"
            "    reward = InviteReward.objects.get(pk=pk, status='pending')\n"
        )
        tmp = tempfile.NamedTemporaryFile('w', suffix='.py', encoding='utf-8',
                                          delete=False)
        self.addCleanup(os.unlink, tmp.name)
        with tmp:
            tmp.write(fake)
        code = function_code(tmp.name, 'approve_reward')
        self.assertNotIn('select_for_update', code, 'docstring/注释没被剥掉')
        problems = audit_approve_reward(code)
        self.assertTrue(problems, '注释里的字眼骗过了审计函数')
        self.assertTrue(any('加锁' in p for p in problems), problems)


# ---------------------------------------------------------------------------
# 与 models.py 对齐（真值从模型源码解析，不经过本模块）
# ---------------------------------------------------------------------------

def models_source():
    return (BACKEND / 'apps' / 'users' / 'models.py').read_text(encoding='utf-8')


def class_node(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError('models.py 里没有 %s' % name)


def assigned(class_node_, attr):
    for stmt in class_node_.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == attr:
                    return stmt.value
    raise AssertionError('%s 里没有 %s' % (class_node_.name, attr))


def decimal_places_of(models_tree, class_name, field_name):
    """`models.DecimalField(..., decimal_places=N)` 里的 N。"""
    call = assigned(class_node(models_tree, class_name), field_name)
    assert isinstance(call, ast.Call), '%s.%s 不是一次调用？' % (class_name, field_name)
    for kw in call.keywords:
        if kw.arg == 'decimal_places':
            return kw.value.value
    raise AssertionError('%s.%s 没写 decimal_places' % (class_name, field_name))


class TestAlignmentWithModels(unittest.TestCase):
    """模块里的常量必须与 `apps/users/models.py` 对得上。"""

    def setUp(self):
        self.tree = ast.parse(models_source())

    def test_返利方式与模型_choices_一致(self):
        choices = ast.literal_eval(
            assigned(class_node(self.tree, 'InviteConfig'), 'REBATE_TYPE_CHOICES'))
        parsed = [value for value, _label in choices]
        # 先证明解析面不是空的：解析器抽不出东西时，下面的 assertEqual 会恒真
        self.assertEqual(len(parsed), 3, 'choices 解析出来不是 3 项：%r' % (parsed,))
        self.assertEqual(parsed, ['first', 'every', 'upgrade'])
        self.assertEqual(sorted(parsed), sorted(KNOWN_REBATE_TYPES))

    def test_状态常量与模型_choices_一致(self):
        choices = ast.literal_eval(
            assigned(class_node(self.tree, 'InviteReward'), 'STATUS_CHOICES'))
        statuses = [value for value, _label in choices]
        self.assertEqual(len(statuses), 3, 'choices 解析出来不是 3 项：%r' % (statuses,))
        for value in COUNTED_STATUSES:
            self.assertIn(value, statuses)
        self.assertEqual(COUNTED_STATUSES, (PENDING, APPROVED))
        # rejected 是人工审出来的，不由判定决定
        self.assertNotIn('rejected', COUNTED_STATUSES)

    def test_金额精度与模型字段一致(self):
        """返利记录的两个金额列都是 2 位 —— 判定这边必须用同一把尺。"""
        self.assertEqual(decimal_places_of(self.tree, 'InviteReward', 'reward_amount'), 2)
        self.assertEqual(decimal_places_of(self.tree, 'InviteReward', 'recharge_amount'), 2)
        self.assertEqual(AMOUNT_PLACES, Decimal('0.01'))

    def test_精度解析器对合成样例也有效(self):
        """自证：上面那条依赖的解析器不是「只对当前文件碰巧成立」。"""
        sample = ast.parse(
            'class X:\n'
            '    amount = models.DecimalField("金额", max_digits=8, decimal_places=4)\n')
        self.assertEqual(decimal_places_of(sample, 'X', 'amount'), 4)

    def test_纯模块不碰_Django(self):
        """这个模块能跑在这个测试里，靠的就是它不 import Django —— 把它锁住。"""
        source = (BACKEND / 'apps' / 'users' / 'invite_reward.py')
        imports = []
        for node in ast.walk(ast.parse(source.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Import):
                imports += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or '')
        for name in imports:
            with self.subTest(module=name):
                self.assertFalse(name.startswith('django'), name)
                self.assertFalse(name.startswith('apps'), name)
                self.assertFalse(name.startswith('.'), name)
        self.assertTrue(imports, '一个 import 都没解析到 —— 这条断言等于没写')


if __name__ == '__main__':
    unittest.main()
