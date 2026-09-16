"""图像生成的定价规则 —— 唯一来源。

为什么单独一个模块而不是塞进 views.py：

1. **同一条规则以前在 views.py 里写了两遍** —— 一次在前置余额校验
   （`total_cost = unit_price * n`），一次在 `_deduct_cost` 里
   （`cost = unit_price * n`）。两处都各自带着那行「模型没配单价就用 0.08」
   的兜底，改一处漏一处就漂移。而这两处漂移的后果不是显示错误：
   前置校验按 A 价拦、扣费按 B 价扣，用户就会看到「余额不足」而余额明明够，
   或者反过来把余额扣穿。
2. 这里不 import Django / 不碰数据库，所以可以直接用 unittest 测
   （见 `apps/image_gen/tests/test_pricing.py`）。DB 是 MySQL，测试环境
   起不了库，钱相关的逻辑要是只能靠连库测，就等于没测。
"""
from decimal import Decimal, InvalidOperation

#: 模型没有配置 per_image_price 时使用的兜底单价（元/张）
DEFAULT_PER_IMAGE_PRICE = Decimal('0.08')


def unit_price_of(model) -> Decimal:
    """模型单张价格；未配置（None / 0 / 取不到）时用兜底值。

    ⚠ `AIModel.per_image_price` 的 `default=0`，所以这里的 **0 表示「没配」而不是「免费」**
    —— 与字段的 help_text（「图像生成类模型的单张价格」）一致。
    真要免费，就得把兜底值改成 0，而不是靠字段留空。
    """
    price = getattr(model, 'per_image_price', None)
    if price is None:
        return DEFAULT_PER_IMAGE_PRICE
    try:
        price = Decimal(str(price))
    except (InvalidOperation, ValueError, TypeError):
        return DEFAULT_PER_IMAGE_PRICE
    return price if price > 0 else DEFAULT_PER_IMAGE_PRICE


def image_cost(model, n) -> Decimal:
    """n 张图的总价。

    n 非法（非整数 / <= 0）时返回 0，而不是抛异常：调用方是请求处理器，
    参数合法性由序列化器负责（`n` 已限定 1..5），这里只保证不会因为一个脏值
    把整条请求打成 500。价格本身永远按 `unit_price_of` 算，绝不在这里再写一份。
    """
    try:
        count = int(n)
    except (TypeError, ValueError):
        return Decimal('0')
    if count <= 0:
        return Decimal('0')
    return unit_price_of(model) * count
