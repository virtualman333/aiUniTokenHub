# -*- coding: utf-8 -*-
"""
这里只放**仓库级的文档契约测试**，不是 Django app —— 没有 models / views，
也不在 `INSTALLED_APPS` 里。

为什么不放在 `apps/utils/tests/`：`apps/utils/` 的职责是计费口径与文案
（见 AGENTS.md），把「文档 vs 实现」塞进去只会让两边都说不清自己管什么。
新建一个空目录的代价，低于把一个测试放错地方。
"""
