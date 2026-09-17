# -*- coding: utf-8 -*-
"""依赖契约：`frontend/pnpm-lock.yaml` 的 `importers['.']` 必须与 `frontend/package.json`
逐字对上。

为什么要有它
------------
`AGENTS.md` 的「Dependency And Artifact Gotchas」一节里有两句话，一句是**声称**，
一句是**自认的空档**：

  > the only **tracked** lockfile is `frontend/pnpm-lock.yaml` … run `pnpm install`
  > in `frontend/` to bring `pnpm-lock.yaml` back in step
  > (**verified: its specifiers match `package.json` today**).
  > **Nothing checks that agreement yet**, so a dependency bump followed by the
  > documented `npm install` silently leaves the tracked lockfile stale.

「verified … today」这种话天生会过期，可它写在一份**没有任何东西在验**的文档里。
本仓库连着好几轮的缺陷都是同一个形状（一句话声称了覆盖面，而落点是空的），
这里的落点尤其空：`frontend/` 的包管理器是 pnpm（唯一入库的锁文件是
`pnpm-lock.yaml`），而文档给的安装命令是 `npm install` —— npm **既不读也不写**
那份锁文件。于是升一个依赖之后，锁文件悄悄停在旧的 specifier 上，直到下一个人
（或 CI）拿到「`package.json` 说要 A、锁文件锁的是 B」这两份事实。

锁什么
------
按 pnpm 会记进 importer 段的三个组，两个方向都查：

  - **包名集合**：`package.json` 里有、锁文件里没有（新加的依赖没重新 lock）→ 红；
    锁文件里有、`package.json` 里没有（删了依赖没重新 lock）→ 也红。
  - **specifier 值**：`^2.3.1` vs `^2.3.0` 这种「升了版本但锁文件没跟」是最常见的
    一种，它**不会**让任何东西报错，只会让下一个人的依赖树和你不一致。

刻意**不**锁：`version:` 那一行（那是解析结果，跟着 registry 走，不属于契约）、
依赖在文件里的顺序、`settings:` / `packages:` 段、以及 `peerDependencies`（pnpm 的
importer 段不记它，本仓目前也没有 —— 真加了得先核对 pnpm 的行为，别想当然）。
也**没有白名单**：一个依赖只能在两处出现，要么两边都有，要么两边都没有。

为什么不用 YAML 库
------------------
这一层结构足够规整（固定缩进、只要三层），而 `apps/*/tests/` 这一层的约定是
**纯标准库、不碰数据库、不碰 Django** —— `python run_tests.py` 要能在没装任何东西的
环境里直接跑起来。多引一个 YAML 依赖换来的只是「少写 40 行」。

假锁防护
--------
`TestScanSurface` 是扫描面自证，缺了它上面那些断言在解析器写坏时会全部恒真：

  - 拿一段**手写的最小锁文件**断言解析结果逐字正确（比拿真文件更细：能定位到
    组名、引号、缩进这三类最容易写坏的地方）；
  - 拿**真锁文件**断言真的解析出了 20 个以上的包（解析器退化成空字典时当场现形）；
  - 在临时目录里造一对「只差一个 specifier」的文件，断言检查**真的报红并且点名**，
    再拿一对一致的文件断言不报 —— 负向验证写进测试，不靠人手改一遍文件再改回来。

跑法（在 backend/ 下）：python run_tests.py
"""
import json
import re
import tempfile
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
ROOT = BACKEND.parent
FRONTEND = ROOT / 'frontend'
PACKAGE_JSON = FRONTEND / 'package.json'
PNPM_LOCK = FRONTEND / 'pnpm-lock.yaml'

#: pnpm 记进 `importers.<路径>` 的依赖组（`peerDependencies` 不在内，见文件头）。
DEP_GROUPS = ('dependencies', 'devDependencies', 'optionalDependencies')

_TOP_LEVEL_RE = re.compile(r'^\S')
_ROOT_IMPORTER_RE = re.compile(r'^  \.:\s*$')
_GROUP_RE = re.compile(r'^    ([A-Za-z]+):\s*$')
_PACKAGE_RE = re.compile(r"^      '?([^':]+)'?:\s*$")
_SPECIFIER_RE = re.compile(r'^        specifier:\s*(.+?)\s*$')


def _unquote(value):
    """去掉 YAML 里可能给标量加的单/双引号（`specifier: '^1.0.0'`）。"""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in '\'"':
        return value[1:-1]
    return value


def parse_lockfile_importers(text):
    """取出 `importers['.']` → `{组名: {包名: specifier}}`。

    只认根 importer：`frontend/` 是单包工程，`packages/` 段与别的 importer
    与这份契约无关（多 workspace 的话要按 importer 路径分别比，那时这条检查得重写）。
    """
    groups = {}
    in_importers = False
    in_root = False
    group = None
    name = None
    for line in text.splitlines():
        if _TOP_LEVEL_RE.match(line):
            in_importers = line.rstrip() == 'importers:'
            in_root = False
            group = name = None
            continue
        if not in_importers:
            continue
        if _ROOT_IMPORTER_RE.match(line):
            in_root = True
            group = name = None
            continue
        if not in_root:
            continue
        m = _GROUP_RE.match(line)
        if m:
            group = m.group(1)
            groups.setdefault(group, {})
            name = None
            continue
        m = _PACKAGE_RE.match(line)
        if m and group:
            name = m.group(1)
            groups[group].setdefault(name, '')
            continue
        m = _SPECIFIER_RE.match(line)
        if m and group and name:
            groups[group][name] = _unquote(m.group(1))
            continue
    return groups


def package_groups(pkg):
    """`package.json` 里我们关心的那几组：`{组名: {包名: specifier}}`。"""
    out = {}
    for group in DEP_GROUPS:
        value = pkg.get(group)
        if isinstance(value, dict):
            out[group] = dict(value)
    return out


def specifier_problems(pkg, lock_text):
    """两份事实之间的差异，返回人类可读的问题清单（空列表 = 契约成立）。"""
    locked = parse_lockfile_importers(lock_text)
    problems = []
    for group in DEP_GROUPS:
        want = (pkg.get(group) or {})
        got = locked.get(group, {})
        for name in sorted(set(want) - set(got)):
            problems.append(
                f'{group}/{name}: package.json 里有，锁文件里没有 —— 补一次 `pnpm install`')
        for name in sorted(set(got) - set(want)):
            problems.append(
                f'{group}/{name}: 锁文件里有，package.json 里没有 —— 补一次 `pnpm install`')
        for name in sorted(set(want) & set(got)):
            if got[name] != want[name]:
                problems.append(
                    f'{group}/{name}: specifier 不一致 —— package.json={want[name]!r}，'
                    f'锁文件={got[name]!r}（多半是用 `npm install` 升的依赖：'
                    f'npm 不读也不写 pnpm-lock.yaml）')
    return problems


def read_package_json(path=PACKAGE_JSON):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def read_lockfile(path=PNPM_LOCK):
    return Path(path).read_text(encoding='utf-8')


class TestFrontendLockfileMatchesPackageJson(unittest.TestCase):
    """契约本身：两侧逐字对上。"""

    def test_lockfile_and_package_json_agree(self):
        problems = specifier_problems(read_package_json(), read_lockfile())
        self.assertEqual(problems, [], (
            'frontend/pnpm-lock.yaml 与 frontend/package.json 对不上 ——\n  '
            + '\n  '.join(problems) +
            '\n在 frontend/ 下跑 `pnpm install` 修好，它才更新得了这份唯一入库的锁文件。'
        ))

    def test_the_comparison_is_not_vacuous(self):
        """两侧都真的有一堆依赖可比 —— 否则上面那条会因为「两边都是空的」而恒真。"""
        pkg = package_groups(read_package_json())
        locked = parse_lockfile_importers(read_lockfile())
        declared = sum(len(v) for v in pkg.values())
        self.assertGreater(declared, 15, f'package.json 只读出 {declared} 个依赖，解析面塌了')
        self.assertGreater(
            sum(len(v) for v in locked.values()), 15,
            '锁文件只解析出这么几个依赖 —— 解析器坏了（真文件里是 20 多个）')

    def test_the_tracked_lockfile_is_the_pnpm_one(self):
        """入库的锁文件是 pnpm 的；`package-lock.json` 不该变成第二份事实。

        只断言它**没有被 git 跟踪**，不断言「不存在」—— 文档给的命令就是 `npm install`，
        照着做的人本地必然有这么一个文件，那是 gitignore 的事（根 .gitignore 已忽略它）。
        """
        self.assertTrue(PNPM_LOCK.is_file(), 'frontend/pnpm-lock.yaml 不见了')
        ignore = (ROOT / '.gitignore').read_text(encoding='utf-8')
        self.assertIn('package-lock.json', ignore, (
            '根 .gitignore 不再忽略 frontend/package-lock.json —— '
            'npm 会写一份与 pnpm-lock.yaml 并存的锁文件，那就是同一件事两份事实'))


class TestScanSurface(unittest.TestCase):
    """扫描面自证：解析器真的在解析，检查真的会红。"""

    MINIMAL_LOCK = """\
lockfileVersion: '9.0'

settings:
  autoInstallPeers: true

importers:

  .:
    dependencies:
      axios:
        specifier: ^1.6.7
        version: 1.16.0
      '@element-plus/icons-vue':
        specifier: ^2.3.1
        version: 2.3.2(vue@3.5.33)
    devDependencies:
      vite:
        specifier: ^5.1.4
        version: 5.4.20(@types/node@20.0.0)

packages:

  axios@1.16.0:
    resolution: {integrity: sha512-deadbeef}
"""

    def test_parser_reads_the_minimal_lockfile_exactly(self):
        """手写样本：组名、带引号的包名、缩进三层，逐字比对。"""
        self.assertEqual(
            parse_lockfile_importers(self.MINIMAL_LOCK),
            {
                'dependencies': {
                    'axios': '^1.6.7',
                    '@element-plus/icons-vue': '^2.3.1',
                },
                'devDependencies': {'vite': '^5.1.4'},
            })
        # `packages:` 段必须被挡住 —— 它里面也有 6 空格缩进的键，混进来会污染结果
        self.assertNotIn('axios@1.16.0', parse_lockfile_importers(self.MINIMAL_LOCK)['dependencies'])

    def test_parser_reads_the_real_lockfile(self):
        locked = parse_lockfile_importers(read_lockfile())
        self.assertGreaterEqual(
            sum(len(v) for v in locked.values()), 20,
            f'真锁文件只解析出 {sum(len(v) for v in locked.values())} 个依赖 —— 解析器退化了')
        self.assertIn('dependencies', locked)
        self.assertIn('devDependencies', locked)

    def test_a_stale_specifier_is_reported_and_named(self):
        """★ 负向：把 specifier 改坏一格，检查必须报红并点名那个包。"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'package.json').write_text(
                json.dumps({'dependencies': {'axios': '^1.6.7'}, 'devDependencies': {}}),
                encoding='utf-8')
            stale = self.MINIMAL_LOCK.replace('specifier: ^1.6.7', 'specifier: ^1.6.0')
            (tmp / 'pnpm-lock.yaml').write_text(stale, encoding='utf-8')
            # 注入必须先落地：改坏的那一处真的变了，否则下面测的是没被改过的文件
            self.assertNotEqual(stale, self.MINIMAL_LOCK)
            self.assertIn('specifier: ^1.6.0', stale)
            pkg_path, lock_path = tmp / 'package.json', tmp / 'pnpm-lock.yaml'

            problems = specifier_problems(read_package_json(pkg_path), read_lockfile(lock_path))
            self.assertTrue(problems, 'specifier 改了却什么都没报 —— 这条检查是假的')
            self.assertTrue(any('axios' in p for p in problems), problems)
            self.assertTrue(any('^1.6.0' in p and '^1.6.7' in p for p in problems),
                            '报红时要把两份值都写出来，否则看的人还得自己去比：' + str(problems))

    def test_a_package_on_one_side_only_is_reported(self):
        """★ 负向：只在一侧出现的包，两个方向都要报。

        `dayjs` 只写在 package.json 里（新加依赖没重新 lock）；
        `@element-plus/icons-vue` / `vite` 只在锁文件里（删了依赖没重新 lock）。
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'package.json').write_text(
                json.dumps({'dependencies': {'axios': '^1.6.7', 'dayjs': '^1.11.10'},
                            'devDependencies': {}}), encoding='utf-8')
            (tmp / 'pnpm-lock.yaml').write_text(self.MINIMAL_LOCK, encoding='utf-8')
            problems = specifier_problems(read_package_json(tmp / 'package.json'),
                                          read_lockfile(tmp / 'pnpm-lock.yaml'))
            self.assertTrue(any('dayjs' in p and '锁文件里没有' in p for p in problems),
                            '只在 package.json 里的包没被报出来：' + str(problems))
            self.assertTrue(any('icons-vue' in p and 'package.json 里没有' in p for p in problems),
                            '只在锁文件里的包没被报出来：' + str(problems))

    def test_agreeing_files_report_nothing(self):
        """★ 反向对照：一致的一对必须一条都不报（检查不许对着正确的东西喊狼）。"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'package.json').write_text(
                json.dumps({'dependencies': {'axios': '^1.6.7',
                                             '@element-plus/icons-vue': '^2.3.1'},
                            'devDependencies': {'vite': '^5.1.4'}}), encoding='utf-8')
            (tmp / 'pnpm-lock.yaml').write_text(self.MINIMAL_LOCK, encoding='utf-8')
            self.assertEqual(
                specifier_problems(read_package_json(tmp / 'package.json'),
                                   read_lockfile(tmp / 'pnpm-lock.yaml')),
                [])


if __name__ == '__main__':
    unittest.main()
