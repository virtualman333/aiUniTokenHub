# -*- coding: utf-8 -*-
"""测试入口自己也要被锁住 —— `run_tests.py` 是全仓所有后端断言的唯一执行入口。

（这里刻意不写「全仓 N 条断言」那个数字：它是个必然漂移的快照 —— 上一版写的是 282，
而写那句的时候全仓已经不是 282 了。要知道现在多少条，跑一遍它自己会打印。）

为什么要有它
------------
`README.md` 第 129 行对 `run_tests.py` 有两条明确承诺：

  1. 「扫的是 `apps/*/tests/`，**不是写死的清单** —— 清单必然会漂移」
  2. 「某个 `tests/` 目录缺 `__init__.py` 就会**直接失败**，不允许静默少跑」

加上本轮补的第三条（原本没有任何东西管它）：

  3. 「**一个 app 连 `tests/` 目录都没有**就直接失败，除非它在 `NO_TESTS_YET` 里声明过」

而在此之前，全仓没有一条用例测过这个脚本本身。它一旦回归，**症状是"全绿"**：

  - `apps/*/tests` 换成写死的清单 → 新加的包静默不参与，`OK —— N 例全部通过`，
    而 N 少了多少没人知道；
  - `__init__.py` 那道检查被删 → 少了它正是历史上 21 个 dashboard 用例长期没被
    跑过的原因（见 `run_tests.py` 的说明）；
  - `pattern='test_*.py'` 改动 → 整个文件静默不收集。

跑 `python run_tests.py` 的人只会看到一行 `OK`。所以这一层必须由**行为**钉住，
而不是读源码断言（`.py` 里那两句话是长是短都拦不住回归）。

锁什么
------
- **真跑一遍临时 backend 根**（子进程启动副本脚本）：造两个包 → 必须都收到；
  改动目录数 → 结果必须跟着变。这一条同时证明了"不是写死的清单"——
  凭空造的目录不可能出现在任何清单里。
- **缺 `__init__.py` 必须失败**：退出码非 0，且消息点名那个目录。
- **真仓库的每个包都参与**——收上来的包集合必须等于 `apps/*/tests` 的实际集合。
- **扫描面收窄时 `run_tests.py` 自己必须失败**——这条判据在 `collect()` 里无条件
  执行，不能只放在本文件里：本文件里的用例本身就在被扫的范围内，扫描面一收窄
  它们跟着消失（实测：glob 换成写死的单包清单，全仓从 295 例悄悄变成 116 例，
  输出仍是 `OK`、退出码仍是 0）。这里只验证那道守卫还活着。
- **失败时退出码非 0**——CI 只认这一个数字；返回 0 的失败是最彻底的假绿。
- **零覆盖的 app 必须喊出来**（见 `TestUncoveredAppsAreLoud`）：凭空造一个只有
  `models.py` 的 app（**刻意不写 `__init__.py`**，因为真仓库的 `apps/users/`
  就是 namespace package）→ 未声明就得失败并点名；声明过就跑得过、但输出里
  必须点名它，免得那一行 `OK` 被读成「都覆盖到了」；声明过的 app 补上测试之后
  同样要失败（那张表不许烂在那里）。四个方向各一条。
- **扫描面自证**：空的临时根必须失败、名字不匹配的文件不得算作用例、
  `find_test_packages` 缺哪几个 `__init__.py` 就点名哪几个。没有这几条，
  上面的断言可能只是恒真。

跑法（在 backend/ 下）：python run_tests.py
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BACKEND = Path(__file__).resolve().parents[3]
ROOT = BACKEND.parent
RUNNER = BACKEND / 'run_tests.py'

sys.path.insert(0, str(BACKEND))
import run_tests  # noqa: E402  （放在 sys.path 处理之后，与脚本自身的做法一致）

#: 临时 backend 根里的最小可跑用例
MINIMAL_TEST = (
    "import unittest\n"
    "\n"
    "class TestTrivial(unittest.TestCase):\n"
    "    def test_ok(self):\n"
    "        self.assertEqual(1 + 1, 2)\n"
)

#: 一定会失败的一条 —— 用来验证「失败时退出码非 0」
FAILING_TEST = (
    "import unittest\n"
    "\n"
    "class TestBroken(unittest.TestCase):\n"
    "    def test_fails(self):\n"
    "        self.assertEqual(1, 2)\n"
)


def real_test_packages():
    """独立重算一遍「该有哪些包」—— 不用被测实现自己算。"""
    apps = BACKEND / 'apps'
    return sorted(
        (p / 'tests').relative_to(BACKEND).as_posix()
        for p in apps.iterdir()
        if p.is_dir() and (p / 'tests').is_dir()
    )


def real_app_names():
    """独立重算一遍「apps/ 下有哪些 app」—— 不用被测实现自己算。

    刻意**不**按有没有 `__init__.py` 来筛：`apps/dashboard/` 与 `apps/users/`
    都是 namespace package，而 `apps/users/` 恰好就是那个零覆盖的 app。
    """
    apps = BACKEND / 'apps'
    return sorted(
        p.name for p in apps.iterdir()
        if p.is_dir() and not p.name.startswith('_') and not p.name.startswith('.')
    )


def test_file_count(package_rel):
    """包里有几个 `test_*.py`。"""
    return len(list((BACKEND / package_rel).glob('test_*.py')))


class TestRunnerSeesEveryPackage(unittest.TestCase):
    """真仓库：每个包都参与，每个 `test_*.py` 都贡献了用例。"""

    def setUp(self):
        self.suite, self.packages = run_tests.collect()
        self.counts = dict(self.packages)

    def test_packages_match_reality(self):
        self.assertEqual(
            sorted(self.counts),
            real_test_packages(),
            'run_tests.py 收上来的包和 apps/*/tests 的实际集合不一致 —— '
            '少一个包就意味着那个包里的用例从此不会被执行，而输出仍然是 OK',
        )

    def test_totals_add_up(self):
        self.assertGreater(self.suite.countTestCases(), 0, '一条用例都没收到')
        self.assertEqual(
            self.suite.countTestCases(), sum(self.counts.values()),
            '总数与各包之和对不上 —— 收集过程有重复或遗漏',
        )


class TestRunnerRefusesToUnderCollect(unittest.TestCase):
    """扫描面收窄时，`run_tests.py` **自己**必须失败。

    这一节存在的理由：`apps/docs/tests/` 里的用例本身就在被扫的范围内 —— 扫描面一
    收窄，它们跟着一起消失。实测把 `find_test_packages` 的 glob 换成写死的单包清单，
    全仓从 295 例悄悄变成 **116 例**，而输出是 `OK`、退出码是 0：守卫和它守卫的东西
    一起静默失效了。所以判据必须待在 `collect()` 里无条件执行，这里只验证它还活着。
    """

    def setUp(self):
        # 这一节**不**用临时根：进程内那个 `apps` 包已经指向真仓库了，临时根里的模块名
        # 会撞在上面，discovery 收上来的是「导入失败的占位用例」而不是真用例 ——
        # 初版就是这样，`countTestCases() == 2` 看着对，其实两条都是导入错误。
        # 临时根交给上面那个**子进程**测试类（那边没有已加载的同名包）。
        # 这里改为在真仓库上**把清单收窄**，直接模拟那个回归。
        pass

    def test_narrowed_package_list_is_fatal(self):
        """收集清单被收窄 → `collect()` 必须报出「有文件掉在扫描面外」。"""
        only_api_proxy = BACKEND / 'apps' / 'api_proxy' / 'tests'
        with mock.patch.object(
            run_tests, 'find_test_packages', lambda root=None: [only_api_proxy]
        ):
            with self.assertRaises(SystemExit) as ctx:
                run_tests.collect()
        msg = str(ctx.exception)
        self.assertIn(
            'apps/docs/tests/test_test_runner.py', msg,
            '必须点名是哪个文件掉队了 —— 否则没人知道少了什么',
        )
        self.assertIn('glob', msg, '报错要说清「清单必须是 glob」')

    def test_full_package_list_passes_the_same_check(self):
        """反向对照：清单没被动过时不该报错（否则这条守卫会被当成误报而关掉）。"""
        _suite, packages = run_tests.collect()
        self.assertGreaterEqual(len(packages), 5, '真仓库的包不可能这么少')

    def test_barren_discovery_is_fatal(self):
        """discovery 什么都收不上来（等价于 pattern 被改）→ 必须失败。"""
        with mock.patch.object(
            run_tests.unittest.TestLoader, 'discover',
            lambda *a, **k: run_tests.unittest.TestSuite(),
        ):
            with self.assertRaises(SystemExit) as ctx:
                run_tests.collect()
        msg = str(ctx.exception)
        self.assertIn('apps/api_proxy/tests', msg, '必须点名是哪个包')
        self.assertIn('只收到 0 例', msg, '要说清"几个文件、收到几例"')


class TestRunnerOnAFreshBackendRoot(unittest.TestCase):
    """凭空造一个 backend 根跑一遍 —— 证明它真的在扫 glob。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='unitokenhub-runner-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        shutil.copy(RUNNER, self.tmp / 'run_tests.py')
        # 与真仓库一致：apps/ 与各应用目录都**没有** __init__.py（靠 namespace package），
        # 只有 tests/ 里才有 —— 别在这里补上，否则测的就不是真形状了。
        self.add_package('alpha', 'test_alpha.py')
        self.add_package('beta', 'test_beta.py')

    def add_package(self, app, filename):
        d = self.tmp / 'apps' / app / 'tests'
        d.mkdir(parents=True, exist_ok=True)
        (d / '__init__.py').write_text('', encoding='utf-8')
        (d / filename).write_text(MINIMAL_TEST, encoding='utf-8')
        return d

    def run_runner(self):
        return subprocess.run(
            [sys.executable, 'run_tests.py'],
            cwd=str(self.tmp), capture_output=True, text=True,
            encoding='utf-8', errors='replace',
        )

    def test_both_packages_are_collected(self):
        r = self.run_runner()
        self.assertEqual(
            r.returncode, 0,
            f'临时根跑不起来：\n{r.stdout}\n{r.stderr}',
        )
        for app in ('alpha', 'beta'):
            self.assertIn(f'apps/{app}/tests', r.stdout, f'{app} 没被收到')
        self.assertIn('2 例全部通过', r.stdout, '两个包各一条用例，应收到 2 例')
        self.assertIn('测试包 2 个', r.stdout)

    def test_new_package_changes_the_result(self):
        """再加一个包，收到的就必须跟着变 —— 写死的清单过不了这一关。"""
        self.add_package('gamma', 'test_gamma.py')
        r = self.run_runner()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('测试包 3 个', r.stdout, '凭空造出来的第三个包没被扫到 —— 扫描面是写死的？')
        self.assertIn('3 例全部通过', r.stdout)

    def test_non_matching_filename_is_not_collected(self):
        """名字不匹配 `test_*.py` 的文件不算用例 —— 包在、里面的文件不算数。"""
        d = self.add_package('delta', 'test_delta.py')
        (d / 'test_delta.py').unlink()
        (d / 'mytest.py').write_text(MINIMAL_TEST, encoding='utf-8')
        r = self.run_runner()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('测试包 3 个', r.stdout, 'delta 有 tests/ 目录，应被算作一个包')
        self.assertIn(
            '2 例全部通过', r.stdout,
            'delta 里只有 mytest.py（不匹配 test_*.py），不该贡献用例',
        )

    def test_a_failing_case_makes_it_exit_nonzero(self):
        """有失败时退出码必须非 0 —— CI 靠这一个数字判断过没过。"""
        d = self.add_package('omega', 'test_broken.py')
        (d / 'test_broken.py').write_text(FAILING_TEST, encoding='utf-8')
        r = self.run_runner()
        self.assertNotEqual(
            r.returncode, 0,
            '有用例失败了，脚本却返回 0 —— 接进 CI 就是一条永远绿的流水线',
        )
        self.assertIn('FAILED', r.stdout)

    def test_missing_init_is_fatal_not_silent(self):
        """缺 `__init__.py` 必须失败并点名目录 —— 静默少跑是最坏的结果。"""
        (self.tmp / 'apps' / 'beta' / 'tests' / '__init__.py').unlink()
        r = self.run_runner()
        self.assertNotEqual(r.returncode, 0, f'缺 __init__.py 竟然跑成了：\n{r.stdout}')
        self.assertIn('apps/beta/tests', r.stdout + r.stderr,
                      '报错必须点名是哪个目录，否则没人知道该补哪里的 __init__.py')

    def test_init_missing_in_any_package_is_fatal(self):
        """两个包同时缺，两个都要被点名（不能报一个就收工）。"""
        for app in ('alpha', 'beta'):
            (self.tmp / 'apps' / app / 'tests' / '__init__.py').unlink()
        r = self.run_runner()
        self.assertNotEqual(r.returncode, 0)
        out = r.stdout + r.stderr
        for app in ('alpha', 'beta'):
            self.assertIn(f'apps/{app}/tests', out, f'{app} 没被点名')


class TestUncoveredAppsAreLoud(unittest.TestCase):
    """**整个 app 没有测试**这件事必须有人喊出来。

    为什么要有它：`apps/*/tests` 是 glob，它只会告诉你「哪些包有测试」，
    永远不会告诉你「少了哪个包」。在 `check_app_coverage` 之前，
    给一个 app 一行测试都不写，`run_tests.py` 照样输出
    `OK —— N 例全部通过`，而 N 只增不减 —— 谁都看不出来。
    """

    #: 临时环境里那个「已声明、但一条测试都没有」的 app。
    #:
    #: 从前这两条用例借的是真仓库 `NO_TESTS_YET` 里的 `'tickets'`（当时它确实
    #: 长期零覆盖）。2026-09-18 把工单的测试补上、真表清空之后，它们跟着红了 ——
    #: 而它们要验的是**脚本的判据**，不是真仓库当下声明了谁。声明由这里自己造。
    DECLARED = 'legacy'

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='unitokenhub-cover-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        shutil.copy(RUNNER, self.tmp / 'run_tests.py')
        self.declare(self.DECLARED)
        self.add_package('alpha', 'test_alpha.py')

    def declare(self, app):
        """往复制过来的 runner 里补一条 `NO_TESTS_YET` 声明。

        真仓库的那张表现在是空的（8 个 app 全都有测试），所以「已声明的零覆盖
        app」这种局面只能在这里现造 —— 顺带也让这两条用例不再依赖另一个文件的
        内容（那正是它们今天坏掉的原因）。
        """
        runner = self.tmp / 'run_tests.py'
        before = runner.read_text(encoding='utf-8')
        after = before.replace(
            'NO_TESTS_YET = {\n}',
            "NO_TESTS_YET = {\n    '%s': '造出来的，用来验证声明表的两个方向。',\n}" % app,
            1,
        )
        self.assertNotEqual(before, after, '没能在临时 runner 里补上声明 —— 锚点失效了')
        runner.write_text(after, encoding='utf-8')

    def add_package(self, app, filename):
        d = self.tmp / 'apps' / app / 'tests'
        d.mkdir(parents=True, exist_ok=True)
        (d / '__init__.py').write_text('', encoding='utf-8')
        (d / filename).write_text(MINIMAL_TEST, encoding='utf-8')
        return d

    def add_bare_app(self, app):
        """造一个**没有任何测试**的 app —— 刻意不写 `__init__.py`，
        因为真仓库里的 `apps/users/` 就是这样（namespace package）。"""
        d = self.tmp / 'apps' / app
        d.mkdir(parents=True, exist_ok=True)
        (d / 'models.py').write_text('X = 1\n', encoding='utf-8')
        return d

    def run_runner(self):
        return subprocess.run(
            [sys.executable, 'run_tests.py'],
            cwd=str(self.tmp), capture_output=True, text=True,
            encoding='utf-8', errors='replace',
        )

    def test_an_undeclared_bare_app_is_fatal(self):
        """凭空多一个零覆盖的 app、又没声明 → 必须失败并点名它。"""
        self.add_bare_app('orphan')
        r = self.run_runner()
        self.assertNotEqual(
            r.returncode, 0,
            '整个 app 一条测试都没有，脚本却返回 0、还输出 OK —— '
            '这就是 glob 看不见的那一半：\n' + r.stdout,
        )
        out = r.stdout + r.stderr
        self.assertIn('apps/orphan/', out, '报错必须点名是哪个 app')
        self.assertIn('NO_TESTS_YET', out, '要说清「要么加测试，要么声明」')

    def test_naming_it_by_hand_does_not_hide_it_from_the_check(self):
        """反向对照：**补上测试**之后同样的 app 不该再报错（不是「只要目录名不在表里就报」）。"""
        self.add_package('orphan', 'test_orphan.py')
        r = self.run_runner()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('2 例全部通过', r.stdout)

    def test_a_declared_bare_app_passes_and_is_printed(self):
        """声明过的零覆盖 app：跑得过，但**必须在输出里点名** ——
        否则那一行 `OK` 会被读成「都覆盖到了」。"""
        self.add_bare_app(self.DECLARED)
        r = self.run_runner()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('没有任何测试的 app 1 个', r.stdout)
        self.assertIn(f'apps/{self.DECLARED}/', r.stdout, '声明过的零覆盖 app 也要打印出来')
        self.assertIn('一条用例都没有', r.stdout,
                      'OK 那一行附近要提醒「它只覆盖了有测试的包」')

    def test_a_declared_app_that_now_has_tests_is_fatal(self):
        """声明表会腐烂：补了测试却忘了删声明，也必须失败。"""
        self.add_package(self.DECLARED, 'test_legacy.py')   # 表里还挂着它
        r = self.run_runner()
        self.assertNotEqual(
            r.returncode, 0,
            f'{self.DECLARED} 已经有测试了、却还挂在 NO_TESTS_YET 里，脚本却没吭声：\n'
            + r.stdout,
        )
        out = r.stdout + r.stderr
        self.assertIn(f'apps/{self.DECLARED}/', out)
        self.assertIn('已经有测试了', out, '要说清是「表里的那条该删了」')

    def test_collect_itself_refuses_a_bare_app(self):
        """`collect()` 自己也得拦住它，不能只靠 `main()` 那条路径。

        理由和上面那节同源：判据要待在**无条件执行**的地方。程序化调用
        （测试、CI、以后别的入口）走的是 `collect()`，只把检查挂在 `main()` 里
        等于给它们开了一条绕道。
        """
        self.add_bare_app('orphan')
        with self.assertRaises(SystemExit) as ctx:
            run_tests.collect(self.tmp)
        self.assertIn('apps/orphan/', str(ctx.exception))

    def test_check_app_coverage_reports_the_real_repo(self):
        """真仓库：返回的「零覆盖 app」必须等于独立重算出来的集合。"""
        bare = run_tests.check_app_coverage()
        covered = {p.split('/')[1] for p in real_test_packages()}
        expected = sorted(set(real_app_names()) - covered)
        self.assertEqual(bare, expected, '零覆盖 app 的名单和实际情况对不上')

    def test_every_app_is_covered_or_declared(self):
        """真仓库：每个 app 都在「有测试」或「已声明」里 —— 一个都不许漏。"""
        covered = {p.split('/')[1] for p in real_test_packages()}
        declared = set(run_tests.NO_TESTS_YET)
        missed = sorted(set(real_app_names()) - covered - declared)
        self.assertEqual(missed, [], f'这些 app 既没有测试也没声明：{missed}')
        # 反方向：声明表里不该留着已经有测试的 app
        self.assertEqual(sorted(covered & declared), [],
                         '这些 app 已经有测试了，NO_TESTS_YET 里那几行该删了')

    def test_declared_apps_actually_exist(self):
        """声明表里不该留着早就删掉的 app —— 那种条目只会让这张表越来越不可信。"""
        gone = sorted(set(run_tests.NO_TESTS_YET) - set(real_app_names()))
        self.assertEqual(gone, [], f'NO_TESTS_YET 里的这些 app 已经不存在了：{gone}')


class TestScanSurfaceOfTheRunnerContract(unittest.TestCase):
    """扫描面自证 —— 没有这一段，上面几条可能只是恒真。"""

    def test_a_fresh_root_really_changes_things(self):
        """反向自证：空的临时根必须**失败**，否则「扫到了」可能只是脚本里写死的。"""
        tmp = Path(tempfile.mkdtemp(prefix='unitokenhub-empty-'))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        shutil.copy(RUNNER, tmp / 'run_tests.py')
        r = subprocess.run(
            [sys.executable, 'run_tests.py'], cwd=str(tmp),
            capture_output=True, text=True, encoding='utf-8', errors='replace',
        )
        self.assertNotEqual(r.returncode, 0, '空根竟然也 OK —— 这个脚本没在扫目录')
        self.assertIn('没找到任何 apps/*/tests 目录', r.stdout + r.stderr)

    def test_find_test_packages_names_every_missing_init(self):
        """直接调函数：缺哪几个就点名哪几个，且不误伤已经补好的那个。

        （子进程测试只看得到退出码和输出，看不到这个返回值。）
        """
        tmp = Path(tempfile.mkdtemp(prefix='unitokenhub-find-'))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for app in ('one', 'two', 'three'):
            (tmp / 'apps' / app / 'tests').mkdir(parents=True)
        (tmp / 'apps' / 'one' / 'tests' / '__init__.py').write_text('', encoding='utf-8')

        def find():
            return run_tests.find_test_packages(tmp)

        with self.assertRaises(SystemExit) as ctx:
            find()
        msg = str(ctx.exception)
        for app in ('two', 'three'):
            self.assertIn(f'apps/{app}/tests', msg, f'{app} 缺 __init__.py 却没被点名')
        self.assertNotIn(
            'apps/one/tests', msg,
            'one 已经补好了 __init__.py，不该出现在报错里 —— 那会让人以为它也有问题',
        )

        (tmp / 'apps' / 'two' / 'tests' / '__init__.py').write_text('', encoding='utf-8')
        with self.assertRaises(SystemExit) as ctx:
            find()
        self.assertNotIn('apps/two/tests', str(ctx.exception), '补好的那个不该再被点名')
        self.assertIn('apps/three/tests', str(ctx.exception))

        (tmp / 'apps' / 'three' / 'tests' / '__init__.py').write_text('', encoding='utf-8')
        found = find()
        self.assertEqual(
            sorted(d.parent.name for d in found), ['one', 'three', 'two'],
            '都补好之后应把三个目录都返回',
        )

    def test_collect_counts_match_the_files_on_disk(self):
        """扫描面自证：真仓库里收到的包数必须等于 apps/*/tests 的实际个数。"""
        _suite, packages = run_tests.collect()
        self.assertEqual(len(packages), len(real_test_packages()))
        self.assertGreaterEqual(len(packages), 5, '包太少了 —— 扫描面坏了？')


if __name__ == '__main__':
    unittest.main()
