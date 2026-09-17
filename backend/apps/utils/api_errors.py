"""把「表单校验失败」翻成一句给用户看的话 —— **全平台唯一来源**（纯 Python，不 import Django）。

为什么要单独一个模块
--------------------
同一句话在本仓库写了 **13 遍**（`apps/ai_models/views.py` 2 处、`apps/tickets/views.py` 5 处、
`apps/users/views.py` 6 处），每一处长这样：

    errors = serializer.errors
    first_error = list(errors.values())[0][0] if errors else '参数错误'
    return APIResponse.error(str(first_error), 400)

13 份副本的代价不是多敲几行，而是它**假设了 `errors` 的形状**，而这个假设有三处不成立：

1. **值是 dict 的时候也有。** DRF 在嵌套 serializer /「列表字段逐项校验」失败时给的是
   `{'items': {0: {'name': ["必填"]}}}` 这种形状 —— `[0]` 对 dict 是 `KeyError`。
2. **`errors` 本身可能是 list。** `many=True` 的 ListSerializer 校验失败时给的是
   `[{...}, {...}]` —— `.values()` 直接 `AttributeError`。
3. **取到的那个元素未必是字符串。** 可能是 dict 或 list，而调用方紧接着就 `str(...)`
   往 JSON 里塞 —— 用户会看到 `{'name': [...]}` 这种东西。

三种情况都落在「用户填错了表单」这条最常见的路径上，后果是 **500 而不是 400**：
前端拿不到「哪个字段错了」，日志里只有一句 KeyError，而这个接口的输入完全是用户可控的。

所以这里收敛成一处，并把形状判据变成可测的纯逻辑：**输入 → 第一个「看得见的消息」，
取不到 → default**。空 dict、空 list、嵌套 dict、list 形态的 errors、None 都不抛异常。

为什么单独一个文件而不塞进 `apps/utils/response.py`：那个模块管的是**回包格式**，
这里管的是**错误文本的挑选**；而且纯函数放在无 Django 依赖的模块里才测得了 ——
见 `apps/utils/tests/test_api_errors.py`。
"""
from typing import Any, Iterator

#: 挑不出任何消息时给用户看的话（与 13 处旧写法里的兜底一致）
DEFAULT_MESSAGE = '参数错误'


def _first_leaf(value: Any, depth: int = 0) -> Iterator[Any]:
    """按「第一个」的方向往下剥，产出候选消息。

    深度上限只是防有人把 errors 造成环（正常情况下最多两三层）。
    """
    if depth > 8:
        return
    if isinstance(value, dict):
        for key in value:
            for leaf in _first_leaf(value[key], depth + 1):
                yield leaf
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            for leaf in _first_leaf(item, depth + 1):
                yield leaf
        return
    yield value


def first_error_message(errors: Any, default: str = DEFAULT_MESSAGE) -> str:
    """从 `serializer.errors` 里取出**第一条**能给人看的话。

    与旧写法（`list(errors.values())[0][0]`）的差别只落在「形状不标准」的输入上：
    正常形态（`{'字段': ['消息']}`）取到的仍是同一个字段的同一句消息，用户看不到变化。

    **永不抛异常** —— 它存在的理由就是替调用方兜住一个形状不确定的输入，
    而调用方全都站在「用户提交的数据有问题」这条路径上，那里不该再冒出一个 500。
    """
    for leaf in _first_leaf(errors):
        if leaf is None:
            continue
        text = str(leaf).strip()
        if text:
            return text
    return default
