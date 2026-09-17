# -*- coding: utf-8 -*-
"""文档契约：文档里承诺的**可执行命令**必须真的存在，**运行要求**只能有一种写法，
**测试命令的扫描面**与**目录清单**必须与磁盘一致。

为什么要有它
------------
最早的发现都在「自建者第一步会照抄的地方」，而没有任何东西会因为它们变红：

  - `README.md` 的前端部署写着 `npm run build:zip` —— `frontend/package.json`
    里**没有这个脚本**，照抄得到的是 `Missing script: "build:zip"`。而
    `npm run build` 本身已经顺带打包了 zip（AGENTS.md 写对了）。同一件事在
    两份文档里两种说法，其中一种是错的。
  - 「跑起来需要哪个数据库」在四份文档里有**三种**说法：`README.md` 的技术栈表
    写 MySQL 5.7+，**同一份 README 的环境要求写 PostgreSQL 14+**，
    `backend/README.md` 写 MySQL 8+ —— 而 `config/settings.py` 的 `ENGINE` 是
    MySQL，并且专门绕过版本检查以兼容 5.7。照环境要求走的人会去装 PostgreSQL。

后续两轮补的两类，性质一样 —— **文档是唯一没人验证过的产物**：

  - **测试命令的扫描面**。`AGENTS.md` 早就写着 Never enumerate test packages by
    hand in docs or scripts，而这条规矩**没有任何落点**：`backend/README.md` 的
    「## 测试」章把 `unittest discover` 指向 `apps/api_proxy/tests`（116 例）与
    `apps/dashboard/tests`（21 例），权威入口 `run_tests.py` 是 314 例 ——
    三条命令的输出都只写 `OK`。收窄扫描面正是本仓库栽过的那个坑（dashboard 的
    21 个用例因为一次收窄长期没被跑过，而文档写着跑了）。
  - **目录清单**。README 的「项目结构」树只手抄了 users / api_proxy / ai_models，
    紧接着那句「`apps/` 下还有 dashboard、image_gen、tickets、utils」读起来像一份
    完整清单，而 `apps/docs/`（本文件自己的老家）三处都没露面 —— 8 个 app 只写了 7 个。
    结构树是自建者唯一的目录地图，少一个 app，他就不知道那里有东西。

锁什么、不锁什么
----------------
只锁「可执行的承诺有没有落点」，不锁措辞：

  - `npm run <script>` —— 必须存在于 `frontend/package.json` 的 `scripts`
  - `python <x>.py`    —— 文件必须存在（相对 `backend/` 或仓库根）
  - 数据库口径 —— 全仓 md 里的数据库**产品名**只允许一种，且与 `settings.py`
    的 `ENGINE` 一致；出现的**最低版本要求**不得高于 `settings.py` 里
    `REQUIRED_DATABASE` 声明的那个（`5.7` 与 `5.7+` 都算 5.7，不苛求写法一致）
  - 测试命令 —— **围栏代码块**里不许出现 `unittest discover`：它唯一的用途就是
    把扫描面收窄到一个包，而收窄后的输出仍然是 `OK`
  - app 清单 —— README「项目结构」围栏里 `apps/` 节点的直接子节点，必须与
    `backend/apps/` 下的目录**双向**相等（少一个 → 地图不全；多一个 → 地图在骗人）

刻意**不**锁：文档可以完全不提某个脚本（提不提 `npm run preview` 不影响用户），
只有「提了却不存在」才是缺陷。

判据是「**一条能被照着执行的完整写法**」，不是「提到了某个名字」—— 三类检查
各自收窄，都是写这条检查时自己撞出来的：

  - **命令**：`npm run <script>` / `python <x>.py` 只算**可执行上下文**里的
    （围栏代码块 / 列表项 / 表格行），散文段落不算。因为 README 要解释「此前
    写着 `npm run build:zip`，那个脚本从来没有过」，那句话本身就带着一个不存在的
    命令，扫全文会把它判红。被要求敲的命令本来就落在代码块和列表里。
  - **数据库要求**：只算**「产品名 + 版本号」**的写法（`MySQL 5.7+`），光提产品名
    不算。因为 AGENTS.md 整篇都是列表项 —— 它要记下「README 曾经写着一个不用
    的数据库产品」，那句话本身带着那个产品名，按上下文收窄根本挡不住。
    而版本号才是「要求」的形状：真缺陷的三处（README 的 `PostgreSQL 14+`、
    技术栈表的 `MySQL 5.7+`、backend/README 的 `MySQL 8+`）**每一处都带版本号**。
  - **测试命令**：只算**围栏代码块**里的，比上面那条「可执行上下文」还窄一档。
    同样因为 AGENTS.md 整篇是列表项：它记下的那条历史命令
    （`discover -s apps -t .` 不报错地跳过了整个包）本身就是这个形状，
    列表项收窄挡不住它 —— 只能按「是不是被要求照着敲的」收窄。

代价说清楚：写成「需要 PostgreSQL」而不带版本的要求不会被抓到；把收窄的测试命令
写成列表项或散文的文档也不会被抓到。这是刻意接受的 —— 一条会误伤「记录历史」的
检查，写一次复盘就得绕过它一次，那时它就等于被关掉了。`test_billing_path.py`
同样排除了注释、docstring 与日志调用。

假锁防护
--------
末尾的 `TestScanSurface` 是**扫描面自证**：断言真的扫到了文档、真的从 README 里
扫出了 `npm run`、真的扫到了带版本号的数据库要求、真的能从围栏块里抓到一条收窄的
测试命令，**并且断言散文确实被排除在命令扫描之外**（可执行上下文比全文短）。
树的解析器与「少一个 app」的判据也各喂一份合成输入验一遍。没有这一段，
一个写坏的正则、或者一次「顺手把 executable_lines 去掉」的改动，会让整套断言恒真
—— 本仓库栽过一次「断言恒真所以挡不住任何回归」。

跑法（在 backend/ 下）：python run_tests.py
"""
import json
import re
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
ROOT = BACKEND.parent

FRONTEND_PKG = ROOT / 'frontend' / 'package.json'
SETTINGS_PY = BACKEND / 'config' / 'settings.py'

#: 扫描 md 时跳过的目录（依赖 / 虚拟环境 / 产物 —— 那些 md 不是我们的文档）
SKIP_DIRS = {'node_modules', 'venv', '.venv', 'dist', 'dist-srv', 'dist.zip',
             '.git', '__pycache__', 'media', 'logs'}

NPM_RUN_RE = re.compile(r'npm run ([A-Za-z0-9:_.-]+)')
PY_SCRIPT_RE = re.compile(r'python3?\s+([A-Za-z0-9_./-]+\.py)')
#: `MySQL 5.7+` / `PostgreSQL 14+` / `MariaDB 10.6` —— 产品 + 可选版本
DB_RE = re.compile(r'\b(MySQL|MariaDB|PostgreSQL|SQLite)\s*([0-9][0-9.]*\+?)?', re.I)

#: 「照着敲的测试命令」。它唯一的用途就是把扫描面收窄到一个包（`-s apps/<包>/tests`），
#: 而收窄后的输出与全量跑一样是 `OK` —— 本仓库栽过这个坑，见文件头。
UNITTEST_DISCOVER_RE = re.compile(r'\bpython3?\s+-m\s+unittest\s+discover\b')
#: 围栏代码块（``` 之间的内容）
FENCED_BLOCK_RE = re.compile(r'^```[^\n]*\n(.*?)^```', re.M | re.S)
#: README 的「项目结构」小节 + 紧跟其后的围栏块
#: （标题里可能带 emoji —— `## 📁 项目结构`，所以标题部分用 `[^\n]*?` 而不是 `\s*`）
STRUCTURE_BLOCK_RE = re.compile(
    r'^#{2,4}[^\n]*?项目结构[^\n]*\n+```[^\n]*\n(.*?)^```', re.M | re.S
)
#: 树的一行：`│   ├── apps/   # 说明` —— 缩进由「四字符一组」决定，即树的层级
TREE_ENTRY_RE = re.compile(r'^(?P<pre>(?:│   |    )*)(?P<glyph>├── |└── )?(?P<name>[^\s#]+)')

#: ENGINE 后缀 → 文档里该用的产品名
ENGINE_PRODUCT = {
    'mysql': 'MySQL',
    'postgresql': 'PostgreSQL',
    'sqlite3': 'SQLite',
    'oracle': 'Oracle',
}


def markdown_files():
    """仓库里所有的 md 文档（排除依赖与产物目录）。"""
    return sorted(
        p for p in ROOT.rglob('*.md')
        if not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts)
    )


def read(path):
    return path.read_text(encoding='utf-8')


FENCE_RE = re.compile(r'^\s*```')
LIST_ITEM_RE = re.compile(r'^\s*([-*+]\s|\d+[.)]\s)')


def executable_lines(text):
    """只取**可执行上下文**的行：围栏代码块内的行 + 列表项 + 表格行。

    命令既可以是被**要求执行**的，也可以是被**提到**的 —— 只有前者是缺陷。
    详见文件头「锁什么、不锁什么」。
    """
    out = []
    in_fence = False
    for raw in text.split('\n'):
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence or LIST_ITEM_RE.match(raw) or raw.lstrip().startswith('|'):
            out.append(raw)
    return '\n'.join(out)


def fenced_lines(text):
    """只取**围栏代码块**里的行 —— 比 `executable_lines` 再窄一档。

    为什么测试命令要多收窄这一档：`AGENTS.md` 整篇都是列表项，而它必然会写下那条
    历史命令（`discover -s apps -t .` 不报错地跳过了整个包）—— 列表项同样在
    `executable_lines` 的扫描面里，那条记录就会被判成缺陷。详见文件头「代价」。
    """
    return '\n'.join(m.group(1) for m in FENCED_BLOCK_RE.finditer(text))


def structure_tree():
    """README「项目结构」小节里那个围栏树。"""
    m = STRUCTURE_BLOCK_RE.search(read(ROOT / 'README.md'))
    if not m:
        raise AssertionError(
            'README 里找不到带围栏的「项目结构」小节 —— 这条检查的扫描面就没了'
        )
    return m.group(1)


def tree_children(tree_text, node):
    """树的某个节点的**直接**子节点名（去掉结尾的 `/`）。

    `apps/` 在树里是第二层（`│   ├── apps/`），子节点是紧跟其后的第三层
    （`│   │   ├── users/`）：层级 = `├── `/`└── ` 之前那串四字符缩进组的个数。
    只按「树枝符号之前的缩进」判层级，所以根节点（没有树枝符号）不是任何节点的子节点。
    """
    entries = []
    for line in tree_text.split('\n'):
        m = TREE_ENTRY_RE.match(line)
        if not m or not m.group('glyph') or not m.group('name'):
            continue
        entries.append((len(m.group('pre')) // 4, m.group('name').rstrip('/')))

    for i, (depth, name) in enumerate(entries):
        if name != node:
            continue
        out = []
        for d, n in entries[i + 1:]:
            if d <= depth:
                break
            if d == depth + 1:
                out.append(n)
        return out
    return None


def app_tree_diff(tree_text, disk_apps):
    """`(树里有而磁盘上没有, 磁盘上有而树里没有)`；树里找不到 `apps/` 节点时返回 None。"""
    children = tree_children(tree_text, 'apps')
    if children is None:
        return None
    return (sorted(set(children) - set(disk_apps)),
            sorted(set(disk_apps) - set(children)))


def app_dirs_on_disk():
    """**独立**重算一遍 `apps/` 下有哪些 app —— 不用被测实现自己算。

    与 `run_tests.py` 的 `app_dirs()` 同一条口径（不按 `__init__.py` 筛，
    `apps/dashboard/` 与 `apps/users/` 都是 namespace package），但这里自己写一份：
    两边共用一份实现的话，实现错了就两边一起错。
    """
    apps = BACKEND / 'apps'
    return sorted(
        p.name for p in apps.iterdir()
        if p.is_dir() and not p.name.startswith('_') and not p.name.startswith('.')
    )


def database_requirements(text):
    """取出文本里的**数据库要求**：(产品, 版本) —— 只认带版本号的写法。

    「提到一个数据库名」不是要求，「`MySQL 5.7+`」才是。判据的理由见文件头。
    """
    return [(p, v) for p, v in DB_RE.findall(text) if v]


def frontend_scripts():
    return set(json.loads(read(FRONTEND_PKG)).get('scripts', {}))


def declared_database():
    """`settings.py` 里声明的运行数据库要求 —— 「需要什么数据库」的唯一来源。"""
    src = read(SETTINGS_PY)
    m = re.search(r"^REQUIRED_DATABASE\s*=\s*['\"]([^'\"]+)['\"]", src, re.M)
    if not m:
        raise AssertionError(
            'config/settings.py 里找不到 REQUIRED_DATABASE —— '
            '文档的数据库口径就又没有来源了（此前四份文档给出三种说法）'
        )
    engine = re.search(r"'ENGINE'\s*:\s*'django\.db\.backends\.([a-z0-9_]+)", src)
    if not engine:
        raise AssertionError('config/settings.py 里找不到 ENGINE')
    return m.group(1).strip(), engine.group(1)


def version_tuple(text):
    """`8+` → (8,)，`5.7+` → (5, 7)。取不到数字就当 (0,)，不参与比较。"""
    nums = [int(n) for n in re.findall(r'\d+', text or '')[:2]]
    return tuple(nums) if nums else (0,)


def pad(v):
    return (list(v) + [0, 0])[:2]


class TestCommandsHaveLandingPoints(unittest.TestCase):
    """文档里写下的命令，必须真的存在。"""

    def test_npm_run_scripts_exist(self):
        scripts = frontend_scripts()
        self.assertTrue(scripts, 'frontend/package.json 里一个 script 都没有？')
        missing = []
        seen = 0
        for doc in markdown_files():
            for name in set(NPM_RUN_RE.findall(executable_lines(read(doc)))):
                seen += 1
                if name not in scripts:
                    missing.append(f'{doc.relative_to(ROOT).as_posix()} → npm run {name}')
        self.assertTrue(seen, '一份文档里都没扫到 `npm run` —— 正则或扫描面坏了')
        self.assertEqual(
            missing, [],
            '这些命令在文档里被要求执行，但 frontend/package.json 里没有：\n  '
            + '\n  '.join(missing)
            + f'\n实际可用的脚本只有：{sorted(scripts)}',
        )

    def test_python_scripts_exist(self):
        missing = []
        seen = 0
        for doc in markdown_files():
            for name in set(PY_SCRIPT_RE.findall(executable_lines(read(doc)))):
                seen += 1
                candidates = [BACKEND / name, ROOT / name]
                if not any(c.exists() for c in candidates):
                    missing.append(f'{doc.relative_to(ROOT).as_posix()} → python {name}')
        self.assertTrue(seen, '一份文档里都没扫到 `python *.py` —— 正则或扫描面坏了')
        self.assertEqual(
            missing, [],
            '这些脚本在文档里被要求执行，但文件不存在（相对 backend/ 与仓库根都找不到）：\n  '
            + '\n  '.join(missing),
        )


class TestDatabaseIsSingleSourced(unittest.TestCase):
    """「跑起来需要哪个数据库」只能有一种写法，且与 ENGINE 一致。"""

    def test_declaration_matches_engine(self):
        declared, engine = declared_database()
        product = ENGINE_PRODUCT.get(engine)
        self.assertIsNotNone(product, f'settings.py 的 ENGINE 后缀 {engine!r} 没登记产品名')
        self.assertEqual(
            product.lower(), declared.split()[0].lower(),
            f'REQUIRED_DATABASE={declared!r} 说的产品与 ENGINE（{engine}）对不上 —— '
            '这就是「两处写法」的开端',
        )

    def test_docs_only_name_the_real_product(self):
        declared, _ = declared_database()
        expected = declared.split()[0].lower()
        found = {}
        for doc in markdown_files():
            for product, _ver in database_requirements(read(doc)):
                found.setdefault(product.lower().capitalize(), set()).add(
                    doc.relative_to(ROOT).as_posix()
                )
        self.assertTrue(found, '一份文档里都没扫到数据库产品名 —— 正则或扫描面坏了')
        wrong = {p: sorted(f) for p, f in found.items() if p.lower() != expected}
        self.assertEqual(
            wrong, {},
            f'文档里出现了不是 {declared.split()[0]} 的数据库：{wrong}\n'
            '自建者会照着去装那个，而 settings.py 连的是 '
            f'{expected}。改文档，别改代码。',
        )

    def test_docs_do_not_require_a_newer_version(self):
        declared, _ = declared_database()
        need = pad(version_tuple(declared))
        too_new = []
        for doc in markdown_files():
            for product, ver in database_requirements(read(doc)):
                if product.lower() != declared.split()[0].lower():
                    continue  # 产品名不对的那条由上一个用例报，不在这里重复
                got = version_tuple(ver)
                if pad(got) > need:
                    here = f'{doc.relative_to(ROOT).as_posix()} 写着 {product} {ver}'
                    too_new.append(here)
        self.assertEqual(
            too_new, [],
            f'文档要求的最低版本高于 REQUIRED_DATABASE（{declared}）：\n  '
            + '\n  '.join(too_new)
            + '\nsettings.py 专门绕过了 Django 的版本检查来兼容更低版本，'
            '把要求写高会劝退本来跑得起来的人。',
        )


class TestTestCommandsKeepTheWholeScanSurface(unittest.TestCase):
    """文档里给出的测试命令，扫描面必须等于全仓 —— 不许手写包清单。

    `AGENTS.md` 有这条规矩（Never enumerate test packages by hand in docs or
    scripts），而它此前**没有任何落点**：`backend/README.md` 的「## 测试」章把
    `unittest discover` 指向 `apps/api_proxy/tests` 与 `apps/dashboard/tests`，
    照着敲分别是 116 例与 21 例，而权威入口 `run_tests.py` 是 314 例 ——
    三条命令的输出都只写 `OK`，差别只在扫描面。收窄扫描面正是本仓库栽过的那个坑：
    `apps/dashboard/` 没有 `__init__.py`，一次性收窄就让它的 21 个用例长期没被跑过，
    而文档写着跑了。
    """

    def test_no_doc_hands_you_a_narrowed_command(self):
        offenders = []
        for doc in markdown_files():
            if UNITTEST_DISCOVER_RE.search(fenced_lines(read(doc))):
                offenders.append(doc.relative_to(ROOT).as_posix())
        self.assertEqual(
            sorted(offenders), [],
            '这些文档在围栏代码块里给出了收窄扫描面的测试命令：\n  '
            + '\n  '.join(sorted(offenders))
            + '\n照着敲的命令只有一条（在 backend/ 下）：python run_tests.py。'
            '\n按包写命令会把扫描面悄悄收窄，而输出仍然是 OK —— 想单独看某个包，'
            '在本地敲就行，别把包名写进文档。',
        )

    def test_the_authoritative_entry_is_actually_documented(self):
        """反向对照：上面那条禁令不能靠「一条测试命令都不写」来满足。

        只断言「围栏里没有收窄命令」的话，把「怎么跑测试」整段删掉同样能过 ——
        那等于把信息删了，而不是把命令修对。
        """
        text = read(BACKEND / 'README.md')
        self.assertIn(
            'python run_tests.py', fenced_lines(text),
            'backend/README.md 必须在围栏代码块里给出权威入口 python run_tests.py —— '
            '自建者只有这一份后端说明，删掉它等于让人自己去猜怎么跑测试',
        )
        self.assertIn(
            'run_tests.py', read(ROOT / 'README.md'),
            '根 README 也要指向权威入口',
        )


class TestProjectStructureListsEveryApp(unittest.TestCase):
    """README 的「项目结构」树里的 app 清单必须与磁盘一致。

    本轮发现：那棵树只手抄了 users / api_proxy / ai_models，紧接着那句
    「`apps/` 下还有 dashboard、image_gen、tickets、utils」读起来像一份完整清单，
    而 `apps/docs/`（本文件自己的老家）三处都没露面 —— 磁盘上 8 个 app 只写了 7 个。
    没有任何东西会因此变红，而且新加一个 app 时同样不会有人提醒。
    """

    def test_tree_matches_the_apps_on_disk(self):
        disk = app_dirs_on_disk()
        self.assertGreaterEqual(len(disk), 5, f'apps/ 下只找到 {disk} —— 路径变了？')
        diff = app_tree_diff(structure_tree(), disk)
        self.assertIsNotNone(
            diff, 'README 的项目结构树里找不到 `apps/` 节点 —— 树被改写了？这条检查得跟着改'
        )
        extra, missing = diff
        self.assertEqual(
            (extra, missing), ([], []),
            'README 的项目结构树与 backend/apps/ 对不上：\n'
            f'  树里有、磁盘上没有：{extra}\n'
            f'  磁盘上有、树里没有：{missing}\n'
            '结构树是自建者唯一的目录地图：少一个 app，他就不知道那里有东西'
            '（`apps/docs/` 就这么一直没被列出来，而它是文档契约测试的老家）；'
            '多一个则是在骗人。',
        )


class TestScanSurface(unittest.TestCase):
    """扫描面自证 —— 没有这一段，写坏的正则会让上面整套断言恒真。"""

    def test_docs_were_actually_found(self):
        docs = [p.relative_to(ROOT).as_posix() for p in markdown_files()]
        self.assertGreaterEqual(len(docs), 5, f'只扫到 {docs} —— rglob 或排除规则坏了')
        for must in ('README.md', 'AGENTS.md', 'backend/README.md'):
            self.assertIn(must, docs, f'{must} 不在扫描面里')
        self.assertNotIn(
            True, [d.startswith('frontend/node_modules') for d in docs],
            '依赖目录里的 md 不该被算进来',
        )

    def test_readme_really_has_commands(self):
        """README 是自建者的第一份文档；它里面一条命令都扫不出来必是正则坏了。"""
        readme = read(ROOT / 'README.md')
        exec_only = executable_lines(readme)
        self.assertGreaterEqual(len(NPM_RUN_RE.findall(exec_only)), 1)
        self.assertGreaterEqual(len(PY_SCRIPT_RE.findall(exec_only)), 1)
        self.assertGreaterEqual(len(database_requirements(readme)), 2,
                                'README 里应至少有两处带版本号的数据库要求（技术栈表 + 环境要求）')
        # 反向自证：散文段落确实被排除在**命令**扫描之外 —— 否则上面两条可能只是
        # 「扫了全文」，而那正是会让这条检查变成雷区、进而被绕开的那个写法。
        self.assertGreater(
            len(readme.split('\n')), len(exec_only.split('\n')),
            '可执行上下文与全文一样长，说明围栏/列表的判定没起作用',
        )
        # 反向自证：产品名 regex 真的能区分「带版本」与「不带版本」
        self.assertEqual(
            database_requirements('本项目用 MySQL，不要换成 PostgreSQL。'),
            [],
            '没有版本号的产品名不该被当成要求 —— 否则 AGENTS.md 那种整篇列表的'
            '规则文件一记历史就变红',
        )
        self.assertEqual(
            database_requirements('- PostgreSQL 14+'),
            [('PostgreSQL', '14+')],
            '带版本号的产品名必须被认出来 —— 这是真缺陷的形状',
        )

    def test_fenced_blocks_really_yield_the_commands(self):
        """围栏块抽取器真的能抓到收窄的测试命令 —— 否则那条禁令恒真。"""
        sample = (
            '想只看协议层可以先跑：\n'
            '\n'
            '```bash\n'
            'cd backend\n'
            'python -m unittest discover -s apps/api_proxy/tests -t . -v\n'
            '```\n'
        )
        self.assertTrue(
            UNITTEST_DISCOVER_RE.search(fenced_lines(sample)),
            '围栏块里的收窄命令抓不到 —— 那条禁令挡不住任何回归（真缺陷就是这个形状）',
        )
        # 反向对照：AGENTS.md 那种「列表项里记录历史」的写法**不该**被抓到。
        # 整篇规则文件都是列表项，它必然要写下那条历史命令的名字。
        agents = read(ROOT / 'AGENTS.md')
        self.assertTrue(
            UNITTEST_DISCOVER_RE.search(agents),
            'AGENTS.md 里本就该有那条历史命令（它记的就是这件事）—— 换个写法说明扫描面变了',
        )
        self.assertIsNone(
            UNITTEST_DISCOVER_RE.search(fenced_lines(agents)),
            'AGENTS.md 的列表项被算成了「照着敲的命令」—— 这条检查会开始误伤历史记录，'
            '写一次复盘就得绕过它一次，最后被关掉',
        )

    def test_the_tree_parser_is_not_vacuous(self):
        """树的解析器按层级收；app 清单的比较两个方向都报得出来。"""
        TREE = (
            'root/\n'
            '├── backend/\n'
            '│   ├── apps/\n'
            '│   │   ├── alpha/\n'
            '│   │   └── beta/\n'
            '│   ├── config/\n'
            '│   │   └── not_an_app/\n'
            '└── frontend/\n'
        )
        self.assertEqual(tree_children(TREE, 'apps'), ['alpha', 'beta'],
                         '解析器没收对 apps/ 的直接子节点（收多了或收少了）')
        self.assertEqual(tree_children(TREE, 'config'), ['not_an_app'],
                         '别的节点的子节点也被收了进来')
        self.assertIsNone(tree_children(TREE, 'nope'), '不存在的节点该返回 None')

        self.assertEqual(
            app_tree_diff(TREE, ['alpha', 'beta']), ([], []),
            '完全一致时不该报差异',
        )
        self.assertEqual(
            app_tree_diff(TREE, ['alpha', 'beta', 'gamma']), ([], ['gamma']),
            '磁盘上多一个 app 时报不出来 —— 那 README 那条锁挡不住「新 app 不露面」',
        )
        self.assertEqual(
            app_tree_diff(TREE, ['alpha']), (['beta'], []),
            '树里写了一个磁盘上没有的 app 时报不出来 —— 那是在骗人',
        )
        self.assertIsNone(app_tree_diff('root/\n', ['alpha']), '没有 apps/ 节点时该返回 None')

        # 真仓库：这条检查的扫描面真的存在
        children = tree_children(structure_tree(), 'apps')
        self.assertIsNotNone(children, '真 README 的结构树里找不到 apps/ 节点')
        self.assertGreaterEqual(len(children), 5, f'只解析出 {children} —— 解析器或树坏了')


if __name__ == '__main__':
    unittest.main()
