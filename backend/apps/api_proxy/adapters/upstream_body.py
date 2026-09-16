# -*- coding: utf-8 -*-
"""发往上游的**流式**请求体 —— 全局唯一一处（纯 Python，不 import Django）。

为什么单独一个模块
------------------
`/v1/chat/completions` 与 `/v1/responses` 各有一条流式分支，此前两边都是同一行
`body['stream'] = True` 了事。看起来只有一个字段，漏掉的那件事却很贵：

**上游不会平白把 usage 送回来。** OpenAI 兼容协议里，流式响应默认**一个 chunk
都不带 `usage`**；要拿到它，请求必须显式带 `stream_options.include_usage = true`
（官方 streaming 参考：设置后会在 `data: [DONE]` 之前多出一个 chunk，它的
`usage` 是整次请求的用量，而 `choices` 恒为空数组）。本仓库从来没有发过这个字段
（全仓 grep `stream_options` 零命中），于是计费完全押在「上游顺手带了 usage」上：

  - 上游带了（不少中转网关确实会带）：正常计费 —— 所以问题一直没暴露；
  - 上游严格按规范不带（OpenAI 自身、以及照规范实现的新网关）：`final_usage`
    是 None → `total_tokens == 0` → 收尾那句 `if ... and total_tokens > 0`
    直接跳过扣费，而 `UsageLog` 的 input/output/total 全是 0。

后一种情况下**用户白用、用量明细全 0**：余额不动、账单没有记录、日志里也没有
异常 —— 与「这次调用真的是免费的」长得一模一样。前端其实一直在读流里的
`usage`（`frontend/src/views/user/Chat/composables/useChat.ts` 的
`if (json.usage)`），也就是说这个字段本来就该有。

由此两条规矩：

1. **索取是默认行为，不是可选项。** 客户端传不传 `stream_options` 都要带上它 ——
   计费不该取决于调用方写没写一个可选参数。
2. **只在 OpenAI 协议下加。** Anthropic 的流自带 usage（`message_start` 的
   `input_tokens`、`message_delta` 里累计的 `output_tokens`），而且它的接口不认
   `stream_options`，塞进去就是 400。

⚠ 打开它会让上游多回一个 `choices: []` 的 chunk，代理**原样转发**给客户端。
   这是协议的既有形状，官方前端读 `json?.choices?.[0]` 已有防护；
   只读 `choices[0]` 的老客户端会在这一个 chunk 上炸 —— 换来的是一次不漏计费。
"""
from typing import Any, Dict, Optional

from .request_adapter import openai_to_anthropic

#: 让上游在流的末尾补一个 usage chunk 的开关。全平台只有这里写它。
STREAM_OPTIONS_INCLUDE_USAGE = 'include_usage'


def build_stream_body(request_data: Optional[Dict[str, Any]],
                      protocol: str = 'openai',
                      model: Optional[str] = None) -> Dict[str, Any]:
    """客户端请求体 → 发往上游的流式请求体。两条流式端点的唯一来源。

    - 一定设置 `stream = True`；
    - OpenAI 协议：**强制** `stream_options.include_usage = True`。
      客户端自己传的 `stream_options` 里的其它键保留（例如
      `continuous_usage_stats`），传了 `None` 或非 dict 也当空表处理 ——
      客户端发 `"stream_options": null` 时不能把强制项吃掉；
    - Anthropic 协议：交给 `openai_to_anthropic` 转换，不加 `stream_options`
      （它用不上，且会 400）；
    - **不修改入参**：调用方还要拿原始请求体去写 `APIAccessLog`。
    """
    body: Dict[str, Any] = dict(request_data or {})
    body['stream'] = True

    if (protocol or 'openai') == 'anthropic':
        return openai_to_anthropic(body, model)

    options = body.get('stream_options')
    options = dict(options) if isinstance(options, dict) else {}
    options[STREAM_OPTIONS_INCLUDE_USAGE] = True
    body['stream_options'] = options
    return body
