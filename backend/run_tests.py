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
  - **一个 app 连 `tests/` 目录都没有** → 也直接失败，除非它出现在下面的
    `NO_TESTS_YET` 里。这是 glob 看不见的那一半：`apps/*/tests` 只会告诉你
    「哪些包有测试」，永远不会告诉你「少了哪个包」。这张表先后顶出过两个长期
    零覆盖的 app，**现在两个都补完了、表也空了**：
      - `apps/users/`（2511 行，`utils.py::process_invite_reward` 就在管钱那条线上）
        —— 把判定抽成 `apps/users/invite_reward.py`，第一套用例落在
        `apps/users/tests/`（2026-09-18）；
      - `apps/tickets/`（468 行，含工单附件的全部规矩）—— 抽成
        `apps/tickets/attachments.py`，用例落在 `apps/tickets/tests/`（同日）。
    两个都是在补上之前**谁都看不出来少了一个 app**：全仓一直输出
    `OK —— N 例全部通过`、总数只增不减。实测：这条检查加上之前，`run_tests.py`
    对这两个 app 的存在与覆盖率一无所知；
  - 每个包打一行用例数，哪些包参与了、各多少条，一眼可查；
  - 打完结果再点一句「哪几个 app 一条测试都没有」—— 免得「OK」被读成「都覆盖到了」。

用法（在 backend/ 下）：
    python run_tests.py

这个脚本自己也被锁住了：上面这些承诺（扫的是 `apps/*/tests` 的 glob、缺
`__init__.py` 就失败、没测试的 app 必须声明）由 `apps/docs/tests/test_test_runner.py`
造临时 backend 根**真跑一遍**验证 —— 这里漏一个包，全仓用例就少跑一批，
而那时所有断言都是绿的。
"""
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parent


#: 一条测试都没有的 app —— 必须在这里露面，并写清为什么。
#:
#: 这不是豁免区，它被两个方向夹着（见 `check_app_coverage`）：
#: 没测试又不在这里 → 失败；在这里却已经有 `tests/` → 也失败。
#: 后一条是为了防止它慢慢变成一块记着陈年旧事的墓碑。
#:
#: **当前是空的**（`apps/` 下 8 个 app 全都有测试了）。它是空的这件事本身也有意义：
#: 哪天新开一个 app，这里不补声明就起不来 —— 而不是等几个月后有人想起来了才发现。
NO_TESTS_YET = {
}


def app_dirs(root=None):
    """`apps/` 下的每个 app 目录（跳掉 `__pycache__` 这类双下划线目录）。

    **不能**用「有没有 `__init__.py`」来判断是不是 app：`apps/dashboard/` 与
    `apps/users/` 都是 namespace package（没有 `__init__.py`），
    而 `apps/users/` 恰好就是那个零覆盖的 app —— 按 `__init__.py` 筛会把最该被
    看见的两个漏掉。
    """
    root = Path(root) if root is not None else BACKEND
    apps_root = root / 'apps'
    if not apps_root.is_dir():
        return []
    return sorted(
        d for d in apps_root.iterdir()
        if d.is_dir() and not d.name.startswith('_') and not d.name.startswith('.')
    )


def check_app_coverage(root=None, declared=None):
    """每个 app 要么有 `tests/`，要么在 `NO_TESTS_YET` 里说明原因。

    返回完全没有测试的 app 名列表（给 `main()` 打印）。
    `declared` 默认就是 `NO_TESTS_YET`；可注入是为了让测试能对任意根目录收一遍，
    跟 `find_test_packages(root)` 同一个路子。

    两个方向都会 `raise SystemExit`：
      - 有 `tests/` 的 app 还挂在声明表里 → 表该瘦身了（补了测试就把那行删掉）；
      - 没有 `tests/` 又没声明的 app → 新 app 必须当场做决定，不许默认零覆盖。

    这一层刻意放在 `collect()` 里**无条件执行**，不放在 `apps/docs/tests/` ——
    理由和第 19 行那段一样：`apps/docs` 自己也是一个 app，那份用例就在被扫的范围内，
    扫描面一收窄，守卫会跟着它守卫的东西一起消失。
    """
    root = Path(root) if root is not None else BACKEND
    table = NO_TESTS_YET if declared is None else declared
    apps_root = root / 'apps'
    if not apps_root.is_dir():
        return []

    names = [d.name for d in app_dirs(root)]
    covered = [n for n in names if (apps_root / n / 'tests').is_dir()]
    bare = [n for n in names if not (apps_root / n / 'tests').is_dir()]

    stale = sorted(n for n in covered if n in table)
    if stale:
        rel = '\n  '.join(f'apps/{n}/' for n in stale)
        raise SystemExit(
            '这些 app 已经有测试了，却还挂在 NO_TESTS_YET 里：\n  ' + rel +
            '\n把这几行删掉 —— 留着会让这张表慢慢变成一块没人看的墓碑，'
            '而它一旦开始骗人，「零覆盖」这条检查就不再可信了。'
        )

    missing = sorted(n for n in bare if n not in table)
    if missing:
        rel = '\n  '.join(f'apps/{n}/' for n in missing)
        raise SystemExit(
            '这些 app 一条测试都没有，也没在 NO_TESTS_YET 里说明原因：\n  ' + rel +
            '\n两个办法，选一个：给它加 apps/<名字>/tests/，'
            '或者在 run_tests.py 的 NO_TESTS_YET 里补一行、写清为什么现在测不了。\n'
            '（glob 只看得见「有测试的包」，一个 app 连 tests/ 目录都没有时它不会报错 ——'
            '不在这里报，就等于默认它永远没人替它看代码。）'
        )

    return sorted(bare)


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

    # 0) 有没有**整个 app** 被漏在外面 —— glob 看不见的那一半。
    #    和上面两条并列、同样无条件执行：收上来的包齐不齐是一回事，
    #    「有没有一个 app 连 tests/ 目录都没有」是另一回事，前者再对也推不出后者。
    check_app_coverage(root)

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
    bare = check_app_coverage()
    suite, packages = collect()

    print(f'测试包 {len(packages)} 个（均不需要数据库）：')
    for name, count in packages:
        print(f'  - {name:<30} {count:>3} 例')

    if bare:
        print(f'\n没有任何测试的 app {len(bare)} 个（已在 NO_TESTS_YET 里声明原因）：')
        for name in bare:
            print(f'  - apps/{name}/  {NO_TESTS_YET[name]}')

    total = suite.countTestCases()
    print(f'\n共 {total} 例，开始执行：\n')
    result = unittest.TextTestRunner(verbosity=1).run(suite)

    print()
    if result.wasSuccessful():
        print(f'OK —— {total} 例全部通过')
        if bare:
            # 这一行是给「OK 被读成『都覆盖到了』」准备的：全绿只说明**已有**的用例通过，
            # 不说明每个 app 都有用例 —— 那是两回事。
            print(
                '（注意：' + '、'.join(f'apps/{n}/' for n in bare) +
                ' 一条用例都没有 —— 上面那行 OK 只覆盖了有测试的包。）'
            )
        return 0
    print(f'FAILED —— {len(result.failures)} 个失败 / {len(result.errors)} 个错误')
    return 1


if __name__ == '__main__':
    sys.exit(main())
