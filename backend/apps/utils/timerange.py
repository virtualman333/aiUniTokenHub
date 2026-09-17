"""把「本地日历日」折成带时区瞬间 —— **全平台唯一来源**（纯 stdlib，不 import Django）。

为什么需要这个模块
------------------
`created_at__date=X` / `TruncDate('created_at')` 在 MySQL 上会被 Django 编译成

    WHERE DATE(CONVERT_TZ(`created_at`, 'UTC', 'Asia/Shanghai')) = %s

`CONVERT_TZ` 的第二个参数是**时区名**，走 MySQL 的时区表（`mysql.time_zone_name`）。
MySQL 默认**不装**这张表，此时 `CONVERT_TZ` 返回 **NULL** —— 整个谓词恒为 NULL，
一条都不匹配，**而且不报错**。实测（本机 + 线上同一个库）：

    SELECT CONVERT_TZ(NOW(), 'UTC', 'Asia/Shanghai');   -- NULL
    SELECT CONVERT_TZ(NOW(), '+00:00', '+08:00');       -- 2026-09-18 14:11:24

于是所有用 `__date` / `TruncDate` 的统计**恒为 0**，界面上是「今日 Token 0 /
今日活跃 0 / 近 7 天活跃 0 / 错误码分布空 / 余额续航『暂无消耗记录』」——
看不出哪里坏了，只是数字永远不动。而 `api_access_logs` 里当时有 1616 条记录。

修法不是换一种 SQL 时区函数（换成显式偏移 `+08:00` 能用，但那等于把时区写死第二遍，
且要依赖 Django 内部对 tzname 的处理），而是**根本不在 SQL 里做时区转换**：
在 Python 里把「本地某一天」算成一个带时区的瞬间，SQL 里只出现

    created_at >= ? AND created_at < ?

这样既不依赖数据库的时区表，也不依赖数据库版本，而且参数由 DB driver 参数化。

为什么是半开区间
----------------
不用 `__lte=<当天 23:59:59.999999>`：MySQL 的 DATETIME(6) 存得下
`23:59:59.9999995` 这种值，而 Python 的 `time.max` 只有 6 位微秒，
尾部会漏掉一行。`[起, 止)` 没有尾部。

时区从哪来
----------
`django.utils.timezone.get_current_timezone()` —— 也就是 `settings.TIME_ZONE`。
这个模块里**不写死任何偏移量**（`+08:00` / `hours=8` / `'Asia/Shanghai'` 一个都不许出现），
写死的那天它就和 settings 漂移了，而漂移是静默的。`day_bounds()` 的 `tz` 参数
**没有默认值**是故意的：有默认值就会出现「忘了传、静默用了 UTC」这种只在早上
8 点前发作的缺陷；`local_day_*()` 那层的 `tz=None` 表示「去问 settings」，
测试则把 tz 显式传进来（所以本模块可以在没有 Django settings 的环境里被裸跑单测）。
"""
from datetime import date, datetime, time, timedelta
import re

__all__ = [
    "current_timezone",
    "day_bounds",
    "dates_back",
    "dates_between",
    "local_day_bounds",
    "local_day_start",
    "parse_day_bound",
]

#: 一天的跨度。单独提出来是为了让「次日零点」这个算式只有一个出处。
_ONE_DAY = timedelta(days=1)

#: 纯日期（`YYYY-MM-DD`）。**不用** `date.fromisoformat` 自己判断：Python 3.11 起
#: 它连 `2026-09-18T15:59:59Z` 这种串也收，然后把时间部分丢掉 —— 于是「带时刻的
#: 上界」会被悄悄当成「整天上界」，窗口比用户选的多出小半天。
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def current_timezone():
    """当前时区。唯一来源是 Django 的 `settings.TIME_ZONE`（惰性导入，见模块 docstring）。

    惰性导入不是洁癖：`django.utils.timezone.get_current_timezone()` 需要
    settings 已配置，放在模块顶层会让这个文件在没有 settings 的环境里 import 失败，
    而下面那些纯函数本身完全不需要 Django。
    """
    from django.utils import timezone as django_timezone

    return django_timezone.get_current_timezone()


def day_bounds(day, tz):
    """`day` 这一天在 `tz` 时区下的 `[起, 止)` 两个瞬间（止 = 次日 00:00）。

    实现用 `datetime.combine(..., tzinfo=tz)`（zoneinfo 语义）。pytz 的
    `replace(tzinfo=...)` 会给出 LMT 偏移（Asia/Shanghai 是 +08:06），
    但本项目没开 `USE_DEPRECATED_PYTZ`，Django 4.2 默认就是 zoneinfo；
    `test_timerange.py` 里有一条断言把偏移钉成整数小时，pytz 混进来会当场红。
    """
    start = datetime.combine(day, time.min, tzinfo=tz)
    return start, start + _ONE_DAY


def local_day_bounds(day, tz=None):
    """`day` 这一本地日在当前时区下的 `[起, 止)`。"""
    return day_bounds(day, tz if tz is not None else current_timezone())


def local_day_start(day, tz=None):
    """`day` 这一本地日的起点。用于「>= 某天零点」这类只有下界的过滤。"""
    return local_day_bounds(day, tz)[0]


def dates_back(count, today):
    """从 `today` 往回数 `count` 天的日期列表，**从早到晚**，末位是 `today`。

    从早到晚是给「按天铺一条曲线」用的：`trend` / `error_analysis` /
    `request_stats` 都按这个顺序产出数据点，反过来会得到一条左右翻转的图。

    `today` 必须由调用方给（view 里传 `timezone.localdate()`）。这里刻意**不**
    自己算「今天」—— 那么做就有第二个「今天」的实现，而两个实现漂移是静默的。

    `count < 1` 返回空列表（不再是「最近 0 天」这种无意义的东西）。
    """
    count = int(count)
    if count < 1:
        return []
    return [today - timedelta(days=offset) for offset in range(count - 1, -1, -1)]


def dates_between(first, last):
    """`[first, last]` 之间的每个日期，从早到晚，**含两端**。

    给「窗口两端都是带时区瞬间」的场景用（`access_stats` 的 `now - N天 .. now`）：
    换算成本地日期之后，首尾两天各只覆盖半天，调用方再拿 `day_bounds` 与窗口取交集，
    这样逐日聚合出来的结果与「按本地日分组」逐行等价。

    顺序反了就自己换过来，不用调用方保证。`first == last` 返回单元素列表。
    """
    if first > last:
        first, last = last, first
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def parse_day_bound(value, *, end=False, tz=None):
    """把「日期筛选」的查询参数解析成一个带时区瞬间；解析不了返回 None。

    两种输入**必须**区别对待，这是本函数存在的全部理由：

    - `YYYY-MM-DD`（Element Plus 的 `value-format="YYYY-MM-DD"`，见
      `frontend/src/views/admin/BillingManagement.vue`）是一整天：
      `end=True` 给**次日零点**（半开区间的上界）。把 `2026-09-18` 直接丢给
      `__lte` 会被 Django 解释成「当天 00:00」—— 结束日那一天的账单一条都查不出来，
      而用户选的时间范围看起来完全正常。
    - 带时刻的 ISO 串（`dayjs(...).toISOString()`，见
      `frontend/src/views/admin/AccessLogs.vue` 的 `startOf('day')` / `endOf('day')`）
      已经是精确瞬间，原样用。这里要是也按「整天」展开，窗口就会比用户选的多出小半天。

    解析不了返回 `None` 而不是抛异常：调用方据此回 **400**（原来把垃圾串直接丢给
    `__gte`，Django 的 `ValidationError` 会变成 500）。

    朴素时刻（没有时区）按当前时区补上 —— 与 Django 对朴素 datetime 的处置一致。
    """
    text = str(value if value is not None else "").strip()
    if not text:
        return None

    if _DATE_ONLY.match(text):
        try:
            day = date.fromisoformat(text)
        except ValueError:
            return None
        return local_day_bounds(day, tz)[1] if end else local_day_start(day, tz)

    # `Z` 手工换掉：`datetime.fromisoformat` 到 3.11 才认 'Z'，服务端 Python 版本
    # 不归这里管，能用 5 行换掉这个前提就用掉。
    normalized = text[:-1] + "+00:00" if text.upper().endswith("Z") else text
    try:
        moment = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=tz if tz is not None else current_timezone())
    return moment
