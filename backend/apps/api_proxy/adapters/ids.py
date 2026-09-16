# -*- coding: utf-8 -*-
"""Chat Completions 的 id → Response API 的 id —— 唯一来源。

这个映射以前在 `response_adapter.py`（非流式）与 `streaming_adapter.py`（流式）
里各写了一份，**逐字相同**。两处漂移的后果不是显示错误：`id` 是客户端串联上下文
用的（`response.previous_response_id`），同一个上游 `chatcmpl-xxx` 在流式与非流式
两条路径上算出不同的 `resp-` id，客户端就再也对不上号 —— 而且只在「先流式再非流式」
这种组合下才现形，极难排查。

放这里还有一个顺带的好处：`streaming_adapter` 的那一份此前没有任何测试覆盖
（`test_adapters.ConvertIdTest` 只测了 `response_adapter` 的那一份），
现在两条路径共用同一个函数，测一次即覆盖两处。
"""


def convert_response_id(chat_id) -> str:
    """`chatcmpl-xxx` → `resp-xxx`；其他形态各自兜底，**绝不让 id 变成空或抛异常**。

    id 在不同上游那边可能是数字，也可能是缺字段（None）。原来的实现直接
    `chat_id.startswith(...)`，遇到 None 会抛 AttributeError，把一次好好的转发
    打成 500 —— 而 id 只是个标识，不该有这种杀伤力。
    """
    text = '' if chat_id is None else str(chat_id)
    if text.startswith('chatcmpl-'):
        return text.replace('chatcmpl-', 'resp-', 1)
    if text.startswith('chatcmpl'):
        return text.replace('chatcmpl', 'resp', 1)
    return f'resp_{text}' if text else 'resp_unknown'
