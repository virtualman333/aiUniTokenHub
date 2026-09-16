"""跨应用共用的工具模块（`response` / `analytics` / `billing`）。

**这个包保持为空，不做任何 re-export** —— 这不是风格偏好，是有具体后果的：

`__init__.py` 里原先有一句 `from .response import APIResponse, ...`，而
`response.py` 依赖 Django/DRF（`rest_framework.response.Response`）。包一旦被
`from apps.utils import billing` 这样导入，`__init__` 会先执行，于是**整个包都
变成了「不装 Django 就 import 不了」**。而本仓库的单元测试契约恰恰是「纯 Python、
不需要 Django settings 和数据库」（见 AGENTS.md），`python run_tests.py` 跑的
就是这种环境 —— 结果是 `apps/utils/` 下的纯逻辑模块根本测不了。

那句 re-export 也没有任何消费者：全仓 12 处调用写的都是显式的
`from apps.utils.response import APIResponse`。删掉它，两种写法就只剩一种。

要加新模块，就加文件，别在这里 re-export。
"""
