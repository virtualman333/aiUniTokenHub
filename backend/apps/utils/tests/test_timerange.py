# -*- coding: utf-8 -*-
"""`apps/utils/timerange.py` 的单元测试 —— 纯 Python，不需要数据库、不需要 Django settings。

为什么这一份值得单独写
----------------------
这个模块是「按本地日查统计」的**唯一地基**：`apps/dashboard/views.py` 与
`apps/api_proxy/views.py` 里所有「今天 / 近 7 天 / 按天铺曲线」都靠它算出来的两个瞬间。
地基错 8 小时，上面每一块统计都跟着错，而且**错得很安静** —— 数字还在，只是归错天。

所以要钉的是三件事，缺一件都拦不住回归：

1. **算术本身**：半开区间 `[起, 止)`、跨月 / 跨年 / 闰日、本地→UTC 的换算。
2. **时区来源只有一个**：`tz=None` 时必须去问 `current_timezone()`（也就是
   `settings.TIME_ZONE`），模块里**不许**出现写死的偏移量。写死的那天它就和
   settings 漂移，而漂移是静默的 —— 这条用**行为断言**（打桩 `current_timezone`
   看它有没有被调用）加**源码断言**（剥掉 docstring 后不许残留 `+08:00` / `Asia/…`
   / `timedelta(hours=…)`）一起钉。
   注意 docstring 里**故意**写着 `'+08:00'` 这些例子（解释为什么不用它们），
   所以源码断言必须先剥字符串字面量，否则这条锁会在正确的代码上判红 ——
   本仓库已经栽过一次「注释里的反面示例被当成实现」。
3. **前提条件还在**：`settings.py` 必须仍然是 `USE_TZ = True`。整个模块的立足点是
   「库里存的是 UTC，所以要在 Python 里把本地零点折成瞬间」；哪天有人把 `USE_TZ`
   关了，`day_bounds` 折出来的瞬间就变成「本地时间再减 8 小时」，所有窗口整体挪 8 小时，
   而没有任何一行代码会报错。
"""
import ast
import re
import unittest
from datetime import date, datetime, timedelta, timezone, time as dtime
from pathlib import Path

from apps.utils import timerange

BACKEND = Path(__file__).resolve().parents[3]
SETTINGS_PY = BACKEND / 'config' / 'settings.py'
TIMERANGE_PY = BACKEND / 'apps' / 'utils' / 'timerange.py'

#: 测试用的固定时区：+08:00。**只出现在测试里** —— 被测模块里必须一个都没有。
TZ8 = timezone(timedelta(hours=8), 'CST')
UTC = timezone.utc


def read(path):
    return path.read_text(encoding='utf-8')


def code_string_constants(src):
    """源码里的字符串字面量，**排除 docstring**。

    排除是必须的：`timerange.py` 的模块与函数 docstring 里逐字引用了
    `'+08:00'` / `'Asia/Shanghai'`（用来解释为什么不这么写）。不剥掉的话，
    这条断言会在**完全正确**的代码上报红，然后被下一个人删掉。
    """
    tree = ast.parse(src)
    docstrings = set()
    for node in ast.walk(tree):
        for attr in ('body', 'orelse', 'finalbody'):
            body = getattr(node, attr, None)
            if not isinstance(body, list):
                continue
            for stmt in body:
                if (
                    isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, ast.Constant)
                    and isinstance(stmt.value.value, str)
                ):
                    docstrings.add(id(stmt.value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


class TestDayBounds(unittest.TestCase):
    """算术：`[起, 止)`、边界、换算。"""

    def test_起点是当天零点(self):
        start, _ = timerange.day_bounds(date(2026, 9, 18), TZ8)
        self.assertEqual(start, datetime(2026, 9, 18, 0, 0, 0, tzinfo=TZ8))

    def test_止点是次日零点且跨度恰好一天(self):
        start, end = timerange.day_bounds(date(2026, 9, 18), TZ8)
        self.assertEqual(end, datetime(2026, 9, 19, 0, 0, 0, tzinfo=TZ8))
        self.assertEqual(end - start, timedelta(days=1))

    def test_半开区间不丢当天的最后一刻(self):
        """`23:59:59.999999` 必须落在区间内 —— 这是不用 `__lte=time.max` 的理由。

        MySQL 的 DATETIME(6) 里 `23:59:59.9999995` 这种值是**存得下**的，
        而 Python 的 `time.max` 只有 6 位微秒（它取 `.replace(microsecond=999999)`），
        尾部会漏。半开区间没有尾部。
        """
        start, end = timerange.day_bounds(date(2026, 9, 18), TZ8)
        last_micro = datetime(2026, 9, 18, 23, 59, 59, 999999, tzinfo=TZ8)
        self.assertLess(last_micro, end)
        self.assertGreaterEqual(last_micro, start)

    def test_前一刻不落在区间内(self):
        start, _ = timerange.day_bounds(date(2026, 9, 18), TZ8)
        self.assertLess(datetime(2026, 9, 17, 23, 59, 59, 999999, tzinfo=TZ8), start)

    def test_跨月(self):
        start, end = timerange.day_bounds(date(2026, 8, 31), TZ8)
        self.assertEqual((start.date(), end.date()), (date(2026, 8, 31), date(2026, 9, 1)))

    def test_跨年(self):
        start, end = timerange.day_bounds(date(2026, 12, 31), TZ8)
        self.assertEqual((start.date(), end.date()), (date(2026, 12, 31), date(2027, 1, 1)))

    def test_闰日(self):
        start, end = timerange.day_bounds(date(2028, 2, 28), TZ8)
        self.assertEqual((start.date(), end.date()), (date(2028, 2, 28), date(2028, 2, 29)))

    def test_本地零点折成UTC就是前一天16点(self):
        """+08:00 的零点 = 前一天的 16:00Z。这张表就是「为什么必须折」的全部内容。"""
        start, end = timerange.day_bounds(date(2026, 9, 18), TZ8)
        self.assertEqual(start.astimezone(UTC), datetime(2026, 9, 17, 16, 0, tzinfo=UTC))
        self.assertEqual(end.astimezone(UTC), datetime(2026, 9, 18, 16, 0, tzinfo=UTC))

    def test_偏移必须是整数小时(self):
        """pytz 的 `replace(tzinfo=...)` 会给出 LMT 偏移（Asia/Shanghai 是 +08:06）。

        本模块用 `datetime.combine(..., tzinfo=tz)`，那是 zoneinfo 语义，正确；
        但哪天有人把 pytz 塞进来（或打开 `USE_DEPRECATED_PYTZ`），所有窗口会整体
        偏 6 分钟 —— 这一条会当场红，而不是等某个月的统计对不上才发现。
        """
        start, _ = timerange.day_bounds(date(2026, 9, 18), TZ8)
        offset = start.utcoffset()
        self.assertIsNotNone(offset)
        self.assertEqual(offset.total_seconds() % 3600, 0, '时区偏移必须是整小时')
        self.assertEqual(offset, timedelta(hours=8))

    def test_零点构造用的就是本地零点(self):
        start, _ = timerange.day_bounds(date(2026, 9, 18), TZ8)
        self.assertEqual(start.timetz().replace(tzinfo=None), dtime(0, 0, 0))


class TestLocalDayBounds(unittest.TestCase):
    """`tz=None` 的分支：必须去问 settings，而不是自己兜一个。"""

    def test_不传时区时去问_current_timezone(self):
        calls = []

        def fake_current_timezone():
            calls.append(1)
            return TZ8

        original = timerange.current_timezone
        timerange.current_timezone = fake_current_timezone
        try:
            start, end = timerange.local_day_bounds(date(2026, 9, 18))
        finally:
            timerange.current_timezone = original

        self.assertEqual(calls, [1], 'tz=None 时必须问 current_timezone()，不许自己兜 UTC')
        self.assertEqual(start, datetime(2026, 9, 18, 0, 0, tzinfo=TZ8))
        self.assertEqual(end, datetime(2026, 9, 19, 0, 0, tzinfo=TZ8))

    def test_显式传入的时区优先于_current_timezone(self):
        def boom():
            raise AssertionError('显式传了 tz 就不该去问 current_timezone()')

        original = timerange.current_timezone
        timerange.current_timezone = boom
        try:
            start, _ = timerange.local_day_bounds(date(2026, 9, 18), UTC)
        finally:
            timerange.current_timezone = original
        self.assertEqual(start, datetime(2026, 9, 18, 0, 0, tzinfo=UTC))

    def test_local_day_start_就是区间的起点(self):
        self.assertEqual(
            timerange.local_day_start(date(2026, 9, 18), TZ8),
            timerange.local_day_bounds(date(2026, 9, 18), TZ8)[0],
        )

    def test_没有_Django_settings_时不传时区会明确报错(self):
        """裸跑（没有 settings）时不许静默兜底成 UTC —— 那会静默错 8 小时。

        这里不真的去 import Django，而是替换掉惰性导入的那一步：只要它**抛**，
        调用方就必须显式给时区，缺陷是响的。
        """
        def exploding():
            raise RuntimeError('settings not configured')

        original = timerange.current_timezone
        timerange.current_timezone = exploding
        try:
            with self.assertRaises(RuntimeError):
                timerange.local_day_bounds(date(2026, 9, 18))
        finally:
            timerange.current_timezone = original


class TestDatesBack(unittest.TestCase):
    """按天铺曲线用的日期序列。"""

    def test_从早到晚且末位是今天(self):
        today = date(2026, 9, 18)
        self.assertEqual(
            timerange.dates_back(7, today),
            [date(2026, 9, 12) + timedelta(days=i) for i in range(7)],
        )

    def test_末位一定是今天(self):
        today = date(2026, 9, 18)
        self.assertEqual(timerange.dates_back(7, today)[-1], today)
        self.assertEqual(timerange.dates_back(1, today), [today])

    def test_长度就是请求的天数(self):
        today = date(2026, 9, 18)
        for n in (1, 2, 7, 30):
            self.assertEqual(len(timerange.dates_back(n, today)), n)

    def test_跨月往回数(self):
        self.assertEqual(
            timerange.dates_back(3, date(2026, 9, 1)),
            [date(2026, 8, 30), date(2026, 8, 31), date(2026, 9, 1)],
        )

    def test_天数小于1返回空(self):
        today = date(2026, 9, 18)
        self.assertEqual(timerange.dates_back(0, today), [])
        self.assertEqual(timerange.dates_back(-3, today), [])


class TestDatesBetween(unittest.TestCase):
    """窗口两端都是「瞬间」时用的日期序列（含两端）。"""

    def test_含两端且从早到晚(self):
        self.assertEqual(
            timerange.dates_between(date(2026, 9, 12), date(2026, 9, 18)),
            [date(2026, 9, 12) + timedelta(days=i) for i in range(7)],
        )

    def test_同一天返回单元素(self):
        self.assertEqual(
            timerange.dates_between(date(2026, 9, 18), date(2026, 9, 18)),
            [date(2026, 9, 18)],
        )

    def test_顺序反了自己换过来(self):
        self.assertEqual(
            timerange.dates_between(date(2026, 9, 18), date(2026, 9, 16)),
            [date(2026, 9, 16), date(2026, 9, 17), date(2026, 9, 18)],
        )

    def test_跨月(self):
        self.assertEqual(
            timerange.dates_between(date(2026, 8, 30), date(2026, 9, 1)),
            [date(2026, 8, 30), date(2026, 8, 31), date(2026, 9, 1)],
        )

    def test_与_dates_back_在等长窗口上结果一致(self):
        today = date(2026, 9, 18)
        self.assertEqual(
            timerange.dates_between(today - timedelta(days=6), today),
            timerange.dates_back(7, today),
        )


class TestParseDayBound(unittest.TestCase):
    """日期筛选参数 → 带时区瞬间。两种输入形态必须区别对待。"""

    def test_纯日期给当天零点(self):
        self.assertEqual(
            timerange.parse_day_bound('2026-09-18', tz=TZ8),
            datetime(2026, 9, 18, 0, 0, tzinfo=TZ8),
        )

    def test_纯日期的上界给次日零点(self):
        """`end=True` 是半开区间的上界 —— 这是「结束日查不出数据」的修复点。"""
        self.assertEqual(
            timerange.parse_day_bound('2026-09-18', end=True, tz=TZ8),
            datetime(2026, 9, 19, 0, 0, tzinfo=TZ8),
        )

    def test_上界不等于当天零点(self):
        """反向对照：直接把 `2026-09-18` 当上界（旧写法）会得到当天 00:00，
        于是结束日一整天的数据被切掉。这一条把「不许退回去」钉住。"""
        self.assertNotEqual(
            timerange.parse_day_bound('2026-09-18', end=True, tz=TZ8),
            datetime(2026, 9, 18, 0, 0, tzinfo=TZ8),
        )

    def test_带Z的时刻原样使用(self):
        got = timerange.parse_day_bound('2026-09-18T15:59:59.999Z', tz=TZ8)
        self.assertEqual(got, datetime(2026, 9, 18, 15, 59, 59, 999000, tzinfo=UTC))
        self.assertEqual(got.astimezone(TZ8), datetime(2026, 9, 18, 23, 59, 59, 999000, tzinfo=TZ8))

    def test_带Z的时刻加不加end都一样(self):
        """带时刻的串已经是精确瞬间，`end` 不该再给它加一天。"""
        open_bound = timerange.parse_day_bound('2026-09-18T15:59:59.999Z', tz=TZ8)
        close_bound = timerange.parse_day_bound('2026-09-18T15:59:59.999Z', end=True, tz=TZ8)
        self.assertEqual(open_bound, close_bound)

    def test_带时刻的串不会被当成整天(self):
        """前端 `dayjs().endOf('day').toISOString()` 的形态：不能被展开成整天。"""
        iso = timerange.parse_day_bound('2026-09-18T15:59:59.999Z', end=True, tz=TZ8)
        whole_day = timerange.parse_day_bound('2026-09-18', end=True, tz=TZ8)
        self.assertLess(iso, whole_day, '带时刻的上界必须比「整天上界」更早')

    def test_朴素时刻按当前时区补时区(self):
        self.assertEqual(
            timerange.parse_day_bound('2026-09-18T12:00:00', tz=TZ8),
            datetime(2026, 9, 18, 12, 0, tzinfo=TZ8),
        )

    def test_解析不了返回None(self):
        for bad in ('abc', '', '   ', None, '2026-13-45', '09/18/2026', '2026-9-8x'):
            self.assertIsNone(timerange.parse_day_bound(bad, tz=TZ8), '不该解析成功：%r' % (bad,))

    def test_date_fromisoformat_确实会吞掉时刻(self):
        """钉住上面那条注释的前提（Python 3.11+ 起的行为）。

        实测：`date.fromisoformat('2026-09-18T15:59:59.999Z')` 返回 `date(2026, 9, 18)`
        —— 时间部分被**丢掉**。所以「用 fromisoformat 能不能解析」不能拿来判断
        「这是不是纯日期」，必须用形状正则。这一条哪天在旧版本 Python 上跑会
        直接抛 ValueError，那正是需要知道的事。
        """
        try:
            parsed = date.fromisoformat('2026-09-18T15:59:59.999Z')
        except ValueError:
            # 老版本 Python（<3.11）会拒绝 —— 那 `_DATE_ONLY` 正则也不是多余的
            return
        self.assertEqual(parsed, date(2026, 9, 18), '前提变了：fromisoformat 不再吞时刻')


class TestSourceContract(unittest.TestCase):
    """源码契约：时区只有 settings 一个来源，模块里不许写死偏移。"""

    def setUp(self):
        self.src = read(TIMERANGE_PY)
        self.strings = code_string_constants(self.src)

    def test_扫描面不许为空(self):
        """剥完 docstring 还剩不下字符串、或者语法解不出来，上面几条就是恒真。"""
        self.assertGreater(len(self.strings), 0, '剥完 docstring 一个字符串都没剩，扫描面失效')
        self.assertTrue(self.strings, '解析面为空')
        # 定点探测：这几句一定存在，锚点没了说明解析方式本身失效了
        joined = ' '.join(self.strings) + self.src
        self.assertIn('local_day_bounds', joined)
        self.assertIn('dates_back', joined)

    def test_不许出现写死的时区偏移(self):
        for s in self.strings:
            for bad in ('+08:00', '+0800', 'Asia/', 'UTC+'):
                self.assertNotIn(
                    bad, s,
                    'timerange.py 里不许写死时区（出现 %r）；时区的唯一来源是 settings.TIME_ZONE' % bad,
                )

    def test_不许用非天单位的_timedelta_拼时区偏移(self):
        """`timedelta(hours=8)` 这类就是「写死偏移」的另一种写法。"""
        tree = ast.parse(self.src)
        offenders = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, 'id', None) or getattr(func, 'attr', None)
            if name != 'timedelta':
                continue
            for kw in node.keywords:
                if kw.arg in ('hours', 'minutes', 'seconds', 'weeks'):
                    offenders.append(kw.arg)
        self.assertEqual(
            offenders, [],
            'timerange.py 里出现了非「天」单位的 timedelta 参数 %r —— 那就是写死的时区偏移' % offenders,
        )

    def test_必须真的去问_settings(self):
        """反向：前面几条不许出现什么，这条要求**必须出现**什么。

        只禁不引的话，把整个模块换成「返回 UTC 零点」也能全绿。
        """
        called = [
            n for n in ast.walk(ast.parse(self.src))
            if isinstance(n, ast.Call)
            and getattr(n.func, 'attr', None) == 'get_current_timezone'
        ]
        self.assertGreaterEqual(
            len(called), 1,
            'timerange.py 必须通过 django.utils.timezone.get_current_timezone() 取时区',
        )

    def test_settings_仍然是_USE_TZ_True(self):
        """前提条件：库里存 UTC。关掉它，所有窗口会整体挪 8 小时且不报错。"""
        src = read(SETTINGS_PY)
        self.assertTrue(
            re.search(r'^\s*USE_TZ\s*=\s*True\s*$', src, re.M),
            'USE_TZ 必须仍是 True —— timerange 的整个立足点是「库里存的是 UTC」',
        )

    def test_settings_里配了时区_name(self):
        src = read(SETTINGS_PY)
        match = None
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith('TIME_ZONE') and '=' in stripped:
                match = stripped.split('=', 1)[1].strip().strip("'\"")
                break
        self.assertIsNotNone(match, 'settings.py 里找不到 TIME_ZONE')
        self.assertTrue(match, 'TIME_ZONE 不许是空串')


if __name__ == '__main__':
    unittest.main()
