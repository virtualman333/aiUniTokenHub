"""上游账号调用统计的口径 —— **只此一处**。

为什么单独一个模块：同一个「成功率」在写入侧（每次请求记一次成败）、
读取侧（上游账号列表接口）、展示侧（管理页的汇总卡片）都要用。各写一份必然
漂移 —— 本仓库已经在「用量解析」上栽过一次（四份实现认得的字段各不相同）。

这里钉住的核心是**分母**：`error_count` 是 `usage_count` 的**子集**（失败的那一次
也计入使用次数，见 `views_openai.update_upstream_usage`），所以分母是 usage_count，
不是 usage_count + error_count。写错的话成功率会整体偏低，而且「全成功」显示成 50%。
"""


def as_count(value) -> int:
    """把统计字段的脏值收敛成**非负整数**。

    不抛异常：这些值来自数据库聚合，一个脏值不该让整个账号列表接口 500
    （本仓库在用量解析上踩过 `int()` 直接抛的坑）。
    """
    if value is None or isinstance(value, bool):
        return 0
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return n if n > 0 else 0


def usage_delta(success: bool) -> tuple[int, int]:
    """一次调用给 `(usage_count, error_count)` 各加多少。

    成功：+1 / +0；失败：+1 / +1 —— 失败**也**算一次使用，
    这样 `error_count <= usage_count` 恒成立，读取侧才敢用 usage 当分母。
    """
    return 1, (0 if success else 1)


def success_rate(usage_count, error_count) -> float:
    """成功率（0~100，一位小数）。

    边界：
      - `usage_count == 0` → **100.0**。没有调用过就没有失败过；
        算成 0% 会把「新加的账号」显示成「全线失败」（这正是修复前的形态）。
      - `error_count > usage_count`（历史脏数据）→ 夹到 0，不吐负数。
    """
    usage = as_count(usage_count)
    errors = as_count(error_count)
    if usage <= 0:
        return 100.0
    errors = min(errors, usage)
    return round((usage - errors) * 100.0 / usage, 1)
