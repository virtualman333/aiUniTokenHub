# -*- coding: utf-8 -*-
"""跑全部后端单元测试（纯 unittest，不需要数据库 / 不需要 Django settings）。

为什么要有这个脚本
------------------
AGENTS.md 里原来的命令是 `python -m unittest discover -s apps/api_proxy/tests -t .`，
后面还跟着一句「Beyond that package there are no backend test files」。后来
`apps/dashboard/tests/`（runway 续航预测）加了进来，那句说明和命令都没跟着改：

  - 按文档那条命令跑，只执行 api_proxy 的包，dashboard 的用例一条都不跑；
  - 换成 `discover -s apps -t .` 也一样漏 —— `apps/dashboard/` 没有 `__init__.py`
    （namespace package），discovery 不会往里递归，而且它**不会报错**，只是少跑。

于是那 21 个用例长期处于「写了但没被跑过」的状态。把包清单写进文档必然漂移，
所以这里直接扫 `apps/*/tests/`：

  - 某个 tests 目录缺 `__init__.py` 会被 discovery 静默跳过 → 这里直接失败，
    不静默（宁可报错也不能假装跑过了）；
  - 每个包打一行用例数，哪些包参与了、各多少条，一眼可查。

用法（在 backend/ 下）：
    python run_tests.py
"""
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parent


def find_test_packages():
    """apps/*/tests —— 缺 __init__.py 的直接报错，不允许被静默跳过。"""
    dirs = sorted(d for d in BACKEND.glob('apps/*/tests') if d.is_dir())
    missing = [d for d in dirs if not (d / '__init__.py').exists()]
    if missing:
        rel = '\n  '.join(d.relative_to(BACKEND).as_posix() for d in missing)
        raise SystemExit(
            '这些 tests 目录缺少 __init__.py，unittest 会静默跳过它们：\n  ' + rel +
            '\n补上空文件即可，否则里面的用例永远不会被执行。'
        )
    return dirs


def main():
    dirs = find_test_packages()
    if not dirs:
        raise SystemExit('没找到任何 apps/*/tests 目录')

    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    print(f'测试包 {len(dirs)} 个（均不需要数据库）：')
    for d in dirs:
        sub = loader.discover(str(d), pattern='test_*.py', top_level_dir=str(BACKEND))
        suite.addTests(sub)
        print(f'  - {d.relative_to(BACKEND).as_posix():<30} {sub.countTestCases():>3} 例')

    total = suite.countTestCases()
    print(f'\n共 {total} 例，开始执行：\n')
    result = unittest.TextTestRunner(verbosity=1).run(suite)

    print()
    if result.wasSuccessful():
        print(f'OK —— {total} 例全部通过')
        return 0
    print(f'FAILED —— {len(result.failures)} 个失败 / {len(result.errors)} 个错误')
    return 1


if __name__ == '__main__':
    sys.exit(main())
