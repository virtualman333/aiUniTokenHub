"""余额续航预测 —— 纯计算，不碰 ORM，可以直接单测。

背景：用户看板此前只统计请求数与 token 数，既不显示余额，也不显示花了多少钱 ——
用户不知道自己还能用多久，只能等扣费失败才发现。这个模块把「消耗速度」和
「剩余余额」合成一句人话能读懂的续航判断。

只做算术，不做 IO：调用方把 (日期, 当日消耗) 的流水喂进来即可。
"""
from datetime import date, timedelta
from decimal import Decimal
from math import ceil

# 默认观察窗口：最近 7 天
DEFAULT_WINDOW = 7
# 续航分级门槛（天）
CRITICAL_DAYS = 3
WATCH_DAYS = 7

LEVEL_TEXT = {
    "empty": "余额已用完",
    "idle": "暂无消耗记录",
    "critical": "余额告急",
    "watch": "留意消耗",
    "safe": "余额充足",
}


def _to_float(value):
    """Decimal / str / None 一律转成 float，避免与 float 混算出精度惊喜。"""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def estimate_runway(daily_costs, balance, *, today=None, window_days=DEFAULT_WINDOW):
    """估算余额还能撑几天。

    :param daily_costs: 可迭代的 (日期, 当日消耗) 二元组，允许乱序、允许含零消耗日
    :param balance: 当前余额
    :param today: 「今天」（默认取系统日期；传入以便测试）
    :param window_days: 观察窗口天数，默认 7

    :return: 见下方各字段。runway_days 为 None 表示算不出来（余额已空或窗口内无消耗）。
    """
    today = today or date.today()
    balance_f = _to_float(balance)

    rows = [(d, _to_float(c)) for d, c in (daily_costs or []) if d is not None]
    if not rows:
        return _result(balance_f, 0, 0, 0.0, None, "idle")

    # 窗口不能超过「账户产生第一条消耗到现在」的跨度：
    # 刚用两天的用户拿 7 天去摊，日均会被摊薄成三分之一，续航虚高。
    earliest = min(d for d, _ in rows)
    span = max(1, (today - earliest).days + 1)
    used_window = max(1, min(int(window_days), span))

    start = today - timedelta(days=used_window - 1)
    in_window = [(d, c) for d, c in rows if start <= d <= today]

    total = sum(c for _, c in in_window)
    active_days = len({d for d, c in in_window if c > 0})
    avg_daily = total / used_window if used_window else 0.0

    if balance_f <= 0:
        return _result(balance_f, used_window, active_days, avg_daily, None, "empty")
    if avg_daily <= 0:
        return _result(balance_f, used_window, active_days, avg_daily, None, "idle")

    runway = int(ceil(balance_f / avg_daily))
    if runway <= CRITICAL_DAYS:
        level = "critical"
    elif runway <= WATCH_DAYS:
        level = "watch"
    else:
        level = "safe"
    return _result(balance_f, used_window, active_days, avg_daily, runway, level, today)


def _result(balance, window_days, active_days, avg_daily, runway_days, level, today=None):
    exhaust_date = None
    if runway_days is not None and today is not None:
        exhaust_date = (today + timedelta(days=runway_days)).isoformat()

    return {
        "balance": round(balance, 6),
        "window_days": window_days,
        "active_days": active_days,
        "avg_daily_cost": round(avg_daily, 6),
        "runway_days": runway_days,
        "exhaust_date": exhaust_date,
        "level": level,
        "level_text": LEVEL_TEXT[level],
        "advice": _advice(level, window_days, active_days, avg_daily, runway_days),
    }


def _advice(level, window_days, active_days, avg_daily, runway_days):
    if level == "empty":
        return "余额已用完，充值后才能继续调用。"
    if level == "idle":
        return "最近没有产生消耗，暂时算不出续航；有调用记录后再来看。"
    days = f"最近 {window_days} 天里有 {active_days} 天在消耗" if window_days > 1 else "今天刚开始消耗"
    return f"按{ days }的速度（日均 ¥{avg_daily:.4f}），余额大约还能用 {runway_days} 天。"
