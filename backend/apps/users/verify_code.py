# -*- coding: utf-8 -*-
"""邮箱验证码的判定 —— **纯 Python，不 import Django**（可被 `run_tests.py` 直接测）。

为什么单独一个模块
------------------
「有没有可用记录 → 过期没 → 内容对不对」这三步此前只写在 `register` 里。本轮补
「忘记密码」时，它会变成**第二份** —— 而「同一件事写两遍」正是本仓反复栽的形状：
改一处、另一处静默不变。这里漂移的代价很具体：**注册能过的码、忘记密码过不了**，
用户看到的只是一句莫名其妙的话，两边代码看起来还都对。

判据本身很短，但它有两样必须一起搬走的东西：

  1. **顺序** —— 先判有没有 → 再判过期 → 最后判内容。顺序错了，「过期」这件事会被
     一句「验证码不正确」盖掉，用户就不知道该重新获取还是该检查自己有没有打错；
  2. **三句话** —— `'请先获取邮箱验证码'` / `'验证码已过期，请重新获取'` / `'验证码不正确'`。
     它们是用户可见的产品文案，只该有一份。

`record` 以**鸭子类型**传进来（只用 `.is_expired` 与 `.code` 两个属性），所以这里不需要
Django —— 测试传一个 `SimpleNamespace` 就够。取记录那一步是 ORM（`purpose` 各不相同），
留在调用方。
"""

#: 通过时的返回值 —— 刻意用 `None` 而不是 `''`：调用方写的是 `if problem:`，
#: 而空串在布尔上下文里是假值，语义不如 `None` 明确（「没有问题」vs「问题是空字符串」）。
NO_PROBLEM = None

#: 三句话的唯一定义处 —— `apps/users/tests/test_verify_code.py` 逐字钉着，并在源码层
#: 反向断言 `views.py` 里不再出现它们的字面量（不然「唯一来源」只是句口号）。
NO_RECORD = '请先获取邮箱验证码'
EXPIRED = '验证码已过期，请重新获取'
MISMATCH = '验证码不正确'


def code_problem(record, code):
    """最新那条未使用的验证码记录（可为 `None`）与提交的 `code` → 问题描述或 `None`。

    返回 `NO_PROBLEM`（即 `None`）才表示通过。
    """
    if record is None:
        return NO_RECORD
    if record.is_expired:
        return EXPIRED
    # 空串两侧同等对待：`'' != ''` 是假，只比 `!=` 的话「没提交码」会撞上「记录里的码也是
    # 空串」而通过 —— 那等于「没发码」就是「码对」。两个调用点上游都拦了空提交
    # （`register` 有一句 `if not code`，`reset_password` 靠 serializer 的 `allow_blank=False`），
    # 这里是判定自己的兜底：判据不该依赖调用方来堵洞。
    if not code or not record.code or record.code != code:
        return MISMATCH
    return NO_PROBLEM
