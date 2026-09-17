# -*- coding: utf-8 -*-
"""环境变量契约：**声明**与**读取**必须对得上，同一件事只能有一种说法。

为什么要有它
------------
本轮的缺陷在 `backend/.env.example` —— 自建者 `cp .env.example .env` 照着填的第一份东西：

  - 模板声明 `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD`，而**全仓没有任何代码读这三个**；
  - 代码只读 `REDIS_URL`（`config/settings.py`），模板里却**没有**这个变量；
  - `README.md` 的环境变量表写的是 `REDIS_URL`（对的）—— 同一件事三处两种说法。

这不是纸面上的不一致，它已经在生效：`backend/.env` 里那三行被照抄并填了真实值
（`REDIS_HOST=47.119.132.60` 与密码），**一行都不起作用**，实际走的是 `settings.py`
的兜底 `redis://127.0.0.1:6379/1` —— 连的是本机那台 Redis，还不带密码。全程不报错，
只是连错了地方（缓存与 `apps/utils/analytics.py` 的流量统计都落在那里）。

同一族的前端：`.env.development` / `.env.production` / `src/vite-env.d.ts` 三处都声明了
`VITE_APP_TITLE` / `VITE_APP_ENV`，而 `src/**` 里零读取。这两个本轮直接删掉 ——
`VITE_APP_TITLE` 也确实没有用途：`index.html` 的标题是刻意写成带 SEO 关键词的长标题
（见 `frontend/SEO-OPTIMIZATION.md`），接上去只会把关键词丢掉。

锁什么
------
两侧都锁，缺一边还是半张网：

  - **声明了必须有人读** —— 否则是在骗自建者：他改了、什么都没发生，也不报错；
  - **读了必须有人声明** —— 否则他根本不知道要配（`REDIS_URL` 当初就是这处境）。

后端：写 `backend/.env.example`，读 `backend/**/*.py`；「必须声明」那一侧只看
`config/settings.py` 的读取点（那是配置的唯一入口，`manage.py` 那种
`os.environ.setdefault('DJANGO_SETTINGS_MODULE', …)` 是**写**不是读，不进扫描面）。
前端：写 `frontend/.env.{development,production}`，读 `frontend/src/**`。

`README.md` 的环境变量表是手抄的第四处，只做**单向**检查：表里写了的必须在模板里有。
反方向不锁 —— 模板才是照抄对象，README 只是速查，少列一个变量不影响谁能把项目跑起来。

刻意**不**锁：变量名风格、默认值、注释措辞、模板里的顺序；也**没有白名单** ——
真要留一个「以后用」的变量，在代码里写一个读取点就行，「声明了没人读」这个口子
正是要堵的东西（留白名单等于把这条检查关掉一半）。
`.env.development` 与 `.env.production` 的变量集合是否相等也不锁 —— 那两处本来就
可以有意不同（比如只想在开发环境打开的开关）。

`*.d.ts` 排除在「读取」之外：类型声明不是使用点，`vite-env.d.ts` 里那句
`readonly VITE_X: string` 只是给 TS 看的 —— 它曾经让两个零读取的变量看起来像在用。

假锁防护
--------
末尾的 `TestScanSurface` 是**扫描面自证**：断言真的解析到了三份模板、真的从代码里
读出了已知变量、README 的表真的被抽出来了、注释行真的不算声明，
并且**喂一个编造的「声明了没人读」的变量进去，检查必须报红**。
没有这一段，一个写坏的正则或一次「顺手把扫描面去掉」的改动会让整套断言恒真 ——
本仓库栽过一次「断言恒真所以挡不住任何回归」。

跑法（在 backend/ 下）：python run_tests.py
"""
import re
import tempfile
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
ROOT = BACKEND.parent
FRONTEND = ROOT / 'frontend'

BACKEND_ENV_EXAMPLE = BACKEND / '.env.example'
SETTINGS_PY = BACKEND / 'config' / 'settings.py'
README = ROOT / 'README.md'
FRONTEND_ENVS = [FRONTEND / '.env.development', FRONTEND / '.env.production']
FRONTEND_SRC = FRONTEND / 'src'

#: 扫源码时跳过的目录（依赖 / 虚拟环境 / 产物 —— 那里面的环境变量不是我们的）
SKIP_DIRS = {'venv', '.venv', 'node_modules', 'dist', 'dist.zip', '.git',
             '__pycache__', 'media', 'logs'}

#: 行首的 `KEY=` —— 注释行由调用方先剔掉
ENV_KEY_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=')
#: `os.getenv('X')` / `os.environ.get('X')` / `os.environ['X']`
PY_READ_RE = re.compile(
    r"""os\.(?:getenv|environ\.get)\(\s*['"]([A-Za-z0-9_]+)['"]"""
    r"""|os\.environ\[\s*['"]([A-Za-z0-9_]+)['"]\s*\]"""
)
#: `import.meta.env.VITE_X`
VITE_READ_RE = re.compile(r'import\.meta\.env\.([A-Za-z0-9_]+)')
#: README 环境变量表的一行：`| KEY | 说明 | 默认值 |`（表头 `| 变量 |` 不匹配）
README_ROW_RE = re.compile(r'^\|\s*`?([A-Z][A-Z0-9_]*)`?\s*\|', re.M)
#: 抽取 README「环境变量」小节
ENV_SECTION_RE = re.compile(r'^#{2,4}\s*环境变量.*$', re.M)


def read(path):
    return path.read_text(encoding='utf-8')


def declared_keys(path):
    """模板里声明的变量名 —— **注释行不算**。

    「记录历史」的说明必然要写出那个已经不用的变量名（本文件开头就在写），
    把注释也算成声明，这套检查立刻变成雷区，写一次复盘就得绕过它一次。
    """
    out = []
    for line in read(path).split('\n'):
        if line.lstrip().startswith('#'):
            continue
        m = ENV_KEY_RE.match(line)
        if m:
            out.append(m.group(1))
    return out


def python_reads(path):
    return {a or b for a, b in PY_READ_RE.findall(read(path))}


def backend_sources():
    return sorted(
        p for p in BACKEND.rglob('*.py')
        if not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts)
    )


def frontend_sources():
    """`frontend/src` 下会真的用到变量的源码 —— `*.d.ts` 不算（类型声明不是使用点）。"""
    return sorted(
        p for p in FRONTEND_SRC.rglob('*')
        if p.suffix in {'.ts', '.js', '.vue', '.tsx', '.jsx'}
        and not p.name.endswith('.d.ts')
        and not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts)
    )


def backend_reads():
    """后端全仓的读取点：变量名 → 文件清单。"""
    out = {}
    for p in backend_sources():
        for k in python_reads(p):
            out.setdefault(k, []).append(p.relative_to(ROOT).as_posix())
    return out


def frontend_reads():
    out = {}
    for p in frontend_sources():
        for k in VITE_READ_RE.findall(read(p)):
            out.setdefault(k, []).append(p.relative_to(ROOT).as_posix())
    return out


def dead_declarations(declared, readers):
    """声明了、但没有任何读取点的变量（配了等于没配）。"""
    return sorted(k for k in declared if k not in readers)


def undeclared_reads(readers, declared):
    """被读了、但模板里没声明的变量（自建者不知道要配）。"""
    return sorted(k for k in readers if k not in declared)


def readme_env_table_keys():
    """README「环境变量」小节里那张表的第一列。"""
    text = read(README)
    m = ENV_SECTION_RE.search(text)
    if not m:
        raise AssertionError(
            'README 里找不到「环境变量」小节 —— 这条检查的扫描面就没了'
        )
    rest = text[m.end():]
    nxt = re.search(r'^#{1,4}\s', rest, re.M)
    section = rest[:nxt.start()] if nxt else rest
    return README_ROW_RE.findall(section)


class TestBackendEnvContract(unittest.TestCase):
    """`backend/.env.example` 与后端代码，两侧必须对得上。"""

    def test_every_declared_var_is_actually_read(self):
        declared = declared_keys(BACKEND_ENV_EXAMPLE)
        self.assertTrue(declared, 'backend/.env.example 里一个变量都没有？')
        dead = dead_declarations(declared, backend_reads())
        self.assertEqual(
            dead, [],
            'backend/.env.example 里这些变量**没有任何代码读** —— 自建者照着模板配了，'
            '一行都不生效，而且不会报错：\n  ' + '\n  '.join(dead) +
            '\n要么删掉它，要么在代码里真的读它（别留一个看起来能配、其实没用的开关）。',
        )

    def test_every_setting_read_is_declared(self):
        reads = python_reads(SETTINGS_PY)
        self.assertTrue(reads, 'config/settings.py 里一个环境变量都没读？')
        missing = undeclared_reads(reads, declared_keys(BACKEND_ENV_EXAMPLE))
        self.assertEqual(
            missing, [],
            'config/settings.py 读了这些变量，而 backend/.env.example 里没有 —— '
            '自建者不知道要配（`REDIS_URL` 当初就是这处境，模板给的是三个读不到的 '
            'REDIS_HOST / REDIS_PORT / REDIS_PASSWORD）：\n  ' + '\n  '.join(missing),
        )


class TestFrontendEnvContract(unittest.TestCase):
    """`frontend/.env.*` 与 `frontend/src/**`，两侧必须对得上。"""

    def _declared(self):
        keys = []
        for p in FRONTEND_ENVS:
            self.assertTrue(p.exists(), f'{p.name} 不存在 —— 扫描面缺了一块')
            keys += declared_keys(p)
        self.assertTrue(keys, '两个 env 文件里一个变量都没有？')
        return keys

    def test_every_declared_var_is_actually_read(self):
        dead = dead_declarations(self._declared(), frontend_reads())
        self.assertEqual(
            dead, [],
            'frontend 的 env 文件里这些变量**没有任何代码读** —— 改了页面不会变，'
            '也不报错：\n  ' + '\n  '.join(dead) +
            '\n（`src/vite-env.d.ts` 里给它们写的类型声明不算「读」，那只是给 TS 看的。）',
        )

    def test_every_read_is_declared(self):
        missing = undeclared_reads(frontend_reads(), self._declared())
        self.assertEqual(
            missing, [],
            'frontend/src 里读了这些变量，而两个 env 文件都没声明 —— '
            '本地能跑是因为代码里有 `|| 兜底`，构建时拿到的是 undefined：\n  '
            + '\n  '.join(missing),
        )


class TestReadmeEnvTable(unittest.TestCase):
    """README 的环境变量表是手抄的第四处，只做单向检查。"""

    def test_readme_only_lists_vars_the_template_has(self):
        keys = readme_env_table_keys()
        self.assertGreaterEqual(len(keys), 5, f'README 的表只抽出 {keys} —— 扫描面坏了')
        declared = set(declared_keys(BACKEND_ENV_EXAMPLE))
        extra = sorted(k for k in keys if k not in declared)
        self.assertEqual(
            extra, [],
            'README 的环境变量表里写着这些变量，但 backend/.env.example 里没有 —— '
            '自建者会照着 README 去填一个模板里不存在的变量：\n  ' + '\n  '.join(extra),
        )


class TestScanSurface(unittest.TestCase):
    """扫描面自证 —— 没有这一段，写坏的正则会让上面整套断言恒真。"""

    def test_templates_were_actually_parsed(self):
        self.assertGreaterEqual(len(declared_keys(BACKEND_ENV_EXAMPLE)), 5,
                                'backend/.env.example 只解析出这么几个 —— 解析器坏了')
        for p in FRONTEND_ENVS:
            self.assertGreaterEqual(len(declared_keys(p)), 1, f'{p.name} 没解析出变量')

    def test_reader_regexes_really_find_reads(self):
        self.assertIn('SECRET_KEY', python_reads(SETTINGS_PY),
                      '连 SECRET_KEY 都读不出来说明 PY_READ_RE 坏了')
        fe = frontend_reads()
        self.assertIn('VITE_API_BASE_URL', fe,
                      '连 VITE_API_BASE_URL 都读不出来说明 VITE_READ_RE 坏了')
        self.assertGreaterEqual(len(fe['VITE_API_BASE_URL']), 2,
                                'VITE_API_BASE_URL 的读取点不该只有一个')

    def test_comments_are_not_declarations(self):
        """「记录历史」的说明必然带着那个已经不用的变量名，它不能被算成声明。"""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / '.env.example'
            p.write_text(
                '# 单列 REDIS_HOST / REDIS_PORT 是读不到的，别照着写\n'
                'REDIS_URL=redis://127.0.0.1:6379/1\n',
                encoding='utf-8',
            )
            self.assertEqual(declared_keys(p), ['REDIS_URL'])

    def test_dts_files_are_not_reads(self):
        """`vite-env.d.ts` 那种 `readonly VITE_X: string` 曾经让死变量看起来像在用。"""
        names = [p.name for p in frontend_sources()]
        self.assertNotIn('vite-env.d.ts', names, '类型声明文件混进了「读取」的扫描面')
        self.assertIn('vite-env.d.ts',
                      [p.name for p in FRONTEND_SRC.rglob('vite-env.d.ts')],
                      'vite-env.d.ts 本身应当还在（只是不参与读取扫描）')

    def test_dead_and_missing_detectors_are_not_vacuous(self):
        """喂编造的输入，两个方向都必须报得出来 —— 恒真的断言挡不住任何回归。"""
        self.assertEqual(
            dead_declarations(['SECRET_KEY', 'NOBODY_READS_ME'], {'SECRET_KEY'}),
            ['NOBODY_READS_ME'],
            '「声明了没人读」这个方向报不出来 —— 那本条轮的真缺陷也拦不住',
        )
        self.assertEqual(
            undeclared_reads({'SECRET_KEY', 'NOBODY_DECLARES_ME'}, {'SECRET_KEY'}),
            ['NOBODY_DECLARES_ME'],
            '「读了没声明」这个方向报不出来 —— REDIS_URL 那类缺陷会再犯一次',
        )


if __name__ == '__main__':
    unittest.main()
