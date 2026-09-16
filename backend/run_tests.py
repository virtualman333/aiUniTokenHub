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
  - 有 `test_*.py` 掉在收集范围之外、或某个包一条用例都没收到 → 也直接失败。
    这两条必须待在**无条件执行**的地方：`apps/docs/tests/` 里那些用例本身就在被
    扫的范围内，扫描面一收窄它们就跟着消失（实测：glob 换成写死的单包清单，
    全仓从 295 例悄悄变成 116 例，退出码还是 0）；
  - 每个包打一行用例数，哪些包参与了、各多少条，一眼可查。

用法（在 backend/ 下）：
    python run_tests.py

这个脚本自己也被锁住了：上面两条承诺（扫的是 `apps/*/tests` 的 glob、缺
`__init__.py` 就失败）由 `apps/docs/tests/test_test_runner.py` 造临时 backend 根
**真跑一遍**验证 —— 这里漏一个包，全仓用例就少跑一批，而那时所有断言都是绿的。
"""
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parent


def find_test_packages(root=None):
    """apps/*/tests —— 缺 __init__.py 的直接报错，不允许被静默跳过。

    `root` 默认 backend 根；之所以可注入，是为了让「它真的在扫 glob，而不是写死的
    清单」这件事能被**真跑一遍**验证（造一个临时 backend 根，看结果跟着变）。
    没有这个参数时，这一层只能靠读源码断言，而源码形态断言挡不住回归。
    """
    root = Path(root) if root is not None else BACKEND
    dirs = sorted(d for d in root.glob('apps/*/tests') if d.is_dir())
    missing = [d for d in dirs if not (d / '__init__.py').exists()]
    if missing:
        rel = '\n  '.join(d.relative_to(root).as_posix() for d in missing)
        raise SystemExit(
            '这些 tests 目录缺少 __init__.py，unittest 会静默跳过它们：\n  ' + rel +
            '\n补上空文件即可，否则里面的用例永远不会被执行。'
        )
    return dirs


def collect(root=None):
    """把该跑的用例收齐：返回 `(suite, [(包的相对路径, 该包用例数)])`。

    单独成一个函数（而不是写在 `main()` 里）是为了让测试能对**任意**根目录收一遍，
    从而验证「每个包都被收到了、每个 test_*.py 都贡献了用例」。

    **扫描面自证也在这里**（下面两段 `raise SystemExit`）：为什么不能只放在
    `apps/docs/tests/test_test_runner.py` 里 —— 因为那些用例本身就在被扫的范围内。
    扫描面一旦收窄，它们跟着一起消失，于是「守卫和它守卫的东西一起静默失效」，
    输出照样是 `OK`。实测：把上面那个 glob 换成写死的单包清单，全仓从 295 例
    悄悄变成 116 例，而退出码是 0。所以这两条判据必须待在**无条件执行**的地方。
    """
    root = Path(root) if root is not None else BACKEND
    dirs = find_test_packages(root)
    if not dirs:
        raise SystemExit('没找到任何 apps/*/tests 目录')

    # 1) 有没有 test_*.py 待在**没被收集的**目录里。
    #    这份清单从文件系统现算，不看 find_test_packages 的返回值 —— 上面那是
    #    glob 时它必然为空，被收窄或写死时才现形。
    strays = [
        f for f in sorted(root.glob('apps/*/tests/test_*.py'))
        if f.parent not in dirs
    ]
    if strays:
        rel = '\n  '.join(f.relative_to(root).as_posix() for f in strays)
        raise SystemExit(
            '这些测试文件所在的目录没被收集，里面的用例永远不会被执行：\n  ' + rel +
            '\n收集清单必须是 apps/*/tests 的 glob（写死或收窄都会静默丢用例）。'
        )

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    packages = []
    for d in dirs:
        sub = loader.discover(str(d), pattern='test_*.py', top_level_dir=str(root))
        suite.addTests(sub)
        packages.append((d.relative_to(root).as_posix(), sub.countTestCases()))

    # 2) 有没有 test_*.py 一条用例都没贡献（pattern 被改、文件名不匹配）。
    #    本仓库的约定：`test_*.py` 就是测试模块，至少贡献一条用例；只放辅助代码的
    #    文件不该带 `test_` 前缀，否则下面会报出来。
    barren = []
    for name, cases in packages:
        files = len(list((root / name).glob('test_*.py')))
        if cases < files:
            barren.append(f'{name}（{files} 个 test_*.py，只收到 {cases} 例）')
    if barren:
        raise SystemExit(
            '这些包里有用例没收上来，多半是 pattern 或文件名的问题：\n  '
            + '\n  '.join(barren) +
            '\n`test_*.py` 至少要贡献一条用例；只放辅助代码的文件请去掉 `test_` 前缀。'
        )

    return suite, packages


def main():
    suite, packages = collect()

    print(f'测试包 {len(packages)} 个（均不需要数据库）：')
    for name, count in packages:
        print(f'  - {name:<30} {count:>3} 例')

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
