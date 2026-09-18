# -*- coding: utf-8 -*-
"""前端分页契约：前端说「我要全部」必须靠翻页，不许靠一个更大的数字。

为什么需要这个文件
------------------
后端 `apps/utils/pagination.py` 把 `page_size` 夹到 `MAX_PAGE_SIZE`（100）。
夹紧本身是对的 —— 以前 `?page_size=999999` 能把整表吐出来。但前端当时有 5 处
用 `1000` / `9999` 表达「我要全部」，夹紧一落地，这些地方就变成**静默截断**：
模型下拉少几项、接口记录导出少几千行，而且全程不报错。

「写一个大数字」和「翻页拿全」在代码里长得几乎一样，只有在数据超过 100 条时
才分岔 —— 所以这里锁三件事：

  1. 前端任何 `page_size` 字面量都不许超过后端上限（静态，全仓扫）；
  2. 说好在翻页的地方要真的在翻页，而且**截断必须说出来**（静态，两向对账）；
  3. `fetchAllPages` 真的会翻页、真的会停、真的会报 truncated（动态，用 node 真跑）。

第 3 块为什么不用文本锁代替
--------------------------
这个助手里面是个 `while` 循环。写错终止条件的后果是**生产环境里转圈转到天荒地老**，
而「循环条件里有没有写 `break`」这种问题，正则看不出来。
本仓的 `.ts` 没有依赖，Node 的 `--experimental-strip-types` 能直接执行它 ——
有条件真跑一遍就别猜。本机没有 node 时整块 skip，不假装通过。
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
FRONTEND = BACKEND.parent / 'frontend'
SRC = FRONTEND / 'src'
HELPER = SRC / 'utils' / 'pagination.ts'

from apps.utils.pagination import MAX_PAGE_SIZE  # noqa: E402

NODE = shutil.which('node')
STRIP_TYPES = '--experimental-strip-types'

CLIENT_EXTS = {'.vue', '.ts', '.js', '.mjs'}
SKIP_DIRS = {'node_modules', 'dist', '.vite'}


# --------------------------------------------------------------------------- 扫描面

def client_sources():
    """`frontend/src` 下所有前端源码。跳过依赖目录与构建产物。

    和 `test_pagination.py::iter_sources` 分开：那边扫的是后端 `apps/`，
    两边各有各的 `tests/` 要排除，硬凑一个函数只会得到一个满是 if 的函数。
    """
    for path in sorted(SRC.rglob('*')):
        if not path.is_file() or path.suffix not in CLIENT_EXTS:
            continue
        rel = path.relative_to(FRONTEND)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        yield rel.as_posix(), path.read_text(encoding='utf-8')


def strip_js_comments(text):
    """把 JS/TS 的注释挖掉，字符串原样保留。

    必须剥：解释「以前这里写的是 1000」的注释、以及本身就在讲这个数字的散文，
    不剥的话锁第一天就红在自己身上 —— 而那时候人只会去改锁。
    字符串不能剥：`page_size` 的字面量就住在字符串里。
    """
    out = []
    i, n = 0, len(text)
    quote = None
    while i < n:
        ch = text[i]
        if quote:
            out.append(ch)
            if ch == '\\' and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in '\'"`':
            quote = ch
            out.append(ch)
            i += 1
            continue
        if ch == '/' and i + 1 < n and text[i + 1] == '/':
            while i < n and text[i] != '\n':
                i += 1
            continue
        if ch == '/' and i + 1 < n and text[i + 1] == '*':
            i += 2
            while i + 1 < n and not (text[i] == '*' and text[i + 1] == '/'):
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


PAGE_SIZE_LITERAL = re.compile(r"\bpage_size\s*:\s*['\"]?(\d+)['\"]?")
FETCH_ALL_CALL = re.compile(r'\bawait\s+fetchAllPages\b')
#: 「截断必须被说出来」的形状。`\s*` 跨行，所以这条不依赖换行怎么写。
TRUNCATED_SAID = re.compile(r'if\s*\(\s*truncated\s*\)\s*\{\s*ElMessage\.warning\(')


def page_size_literals():
    """-> [(rel, lineno, value)]。扫描逻辑只此一处，两条锁共用。"""
    hits = []
    for rel, text in client_sources():
        for lineno, line in enumerate(strip_js_comments(text).splitlines(), start=1):
            match = PAGE_SIZE_LITERAL.search(line)
            if match:
                hits.append((rel, lineno, int(match.group(1))))
    return hits


# ------------------------------------------------------------------- 静态：来源锁

class FrontendSourceLockTests(unittest.TestCase):

    def test_扫描面真的扫到了东西(self):
        # 「没有一个地方超限」是**通行证式**断言：扫描面塌了它照样全绿。
        # 上一轮就栽在这上面（`parents[2]` 扫了个空目录）。所以先把面钉住。
        rels = sorted(rel for rel, _ in client_sources())
        self.assertGreater(len(rels), 40, f'只扫到 {len(rels)} 个前端文件 —— 扫描面大概是错的')
        for known in [
            'src/utils/pagination.ts',
            'src/views/admin/AccessLogs.vue',
            'src/views/admin/ChannelManagement.vue',
            'src/views/admin/ModelManagement.vue',
            'src/views/user/APIDoc.vue',
            'src/views/user/Chat/index.vue',
        ]:
            self.assertIn(known, rels)

    def test_前端的上限就是后端的上限(self):
        code = strip_js_comments(HELPER.read_text(encoding='utf-8'))
        match = re.search(r'export const PAGE_SIZE\s*=\s*(\d+)', code)
        self.assertIsNotNone(match, 'pagination.ts 里找不到 `export const PAGE_SIZE = <数字>`')
        self.assertEqual(
            int(match.group(1)), MAX_PAGE_SIZE,
            f'前端 PAGE_SIZE={match.group(1)} 与后端 MAX_PAGE_SIZE={MAX_PAGE_SIZE} 漂了。'
            ' 两边必须同时改 —— 只改一边的表现是「前端以为能拿 200 条，后端只给 100 条」。',
        )

    def test_上限扫描面真的在匹配(self):
        # 反向对照：同一条正则必须抓住**合法**的字面量，并且抓到的位置对得上。
        # 否则 `test_没有调用点要得比上限更多` 可能只是因为正则瞎了 ——
        # 那种情况下它会一路全绿，而魔法数字照样在代码里。
        hits = {(rel, value) for rel, _, value in page_size_literals()}
        self.assertIn(('src/views/admin/Dashboard.vue', 5), hits,
                      '扫描没读到 Dashboard.vue 里那个合法的 page_size: 5 —— 正则或扫描面有问题')
        self.assertIn(('src/views/user/ImageGen/index.vue', 99), hits,
                      '扫描没读到 ImageGen 里那个合法的 page_size: 99')

    def test_没有调用点要得比上限更多(self):
        offenders = [
            f'{rel}:{lineno} page_size={value}'
            for rel, lineno, value in page_size_literals()
            if value > MAX_PAGE_SIZE
        ]
        self.assertEqual(
            offenders, [],
            '这些地方又用大数字表达「我要全部」了 —— 会被后端静默夹到 '
            f'{MAX_PAGE_SIZE}，改用 frontend/src/utils/pagination.ts 的 fetchAllPages：\n  '
            + '\n  '.join(offenders),
        )


# ----------------------------------------------------------- 静态：用法与截断

class FetchAllPagesUsageTests(unittest.TestCase):
    """两向对账 + 「截断必须被说出来」。

    登记表是双向的：这里写了、代码里没调用 → 红；代码里调用了、这里没登记 → 也红。
    没有例外表 —— 例外表一旦存在就得长期维护，而且它自己会漂。
    """

    USERS = {
        'src/views/admin/AccessLogs.vue',
        'src/views/admin/ChannelManagement.vue',
        'src/views/admin/ModelManagement.vue',
        'src/views/user/APIDoc.vue',
        'src/views/user/Chat/index.vue',
    }

    def _code(self, rel):
        return strip_js_comments((FRONTEND / rel).read_text(encoding='utf-8'))

    def test_用翻页的文件恰好是登记过的那批(self):
        found = {rel for rel, text in client_sources()
                 if FETCH_ALL_CALL.search(strip_js_comments(text))}
        self.assertEqual(
            found, self.USERS,
            '与登记不符：多了 ' + repr(sorted(found - self.USERS)) +
            '，少了 ' + repr(sorted(self.USERS - found)),
        )

    def test_没有哪个文件只_import_不调用(self):
        # 只 import 不调用是最高级的「看起来修好了」。
        for rel, text in client_sources():
            code = strip_js_comments(text)
            if 'fetchAllPages' in code and rel != 'src/utils/pagination.ts' and rel not in self.USERS:
                self.fail(f'{rel} 提到了 fetchAllPages，但登记表里没有它')

    def test_每个翻页调用都把截断说出来了(self):
        # 截断发生在「数据多到 50 页都没装下」时。不报出来的话，用户看到的是
        # 一份少了几行的导出、一个少了几项的下拉 —— 和修之前一模一样。
        for rel in sorted(self.USERS):
            with self.subTest(file=rel):
                code = self._code(rel)
                calls = len(FETCH_ALL_CALL.findall(code))
                said = len(TRUNCATED_SAID.findall(code))
                self.assertGreater(calls, 0, f'{rel} 登记了却没在翻页')
                self.assertEqual(
                    calls, said,
                    f'{rel} 有 {calls} 处翻页但只有 {said} 处把 truncated 说出来了；'
                    ' 每一处都要有 `if (truncated) { ElMessage.warning(...) }`',
                )


# -------------------------------------------------------------- 动态：真跑一遍

_DRIVER = r'''
const url = process.argv[2]
const mod = await import(url)
const out = {}
const rec = (k, v) => { out[k] = v }

function paged(total, log) {
  return async (page, pageSize) => {
    if (log) log.push([page, pageSize])
    const start = (page - 1) * pageSize
    const n = Math.max(0, Math.min(pageSize, total - start))
    return {
      results: Array.from({ length: n }, (_, i) => start + i),
      total, page, page_size: pageSize,
    }
  }
}
const shape = (r, calls) => ({
  len: r.items.length,
  pages: r.pages,
  truncated: r.truncated,
  unpaginated: r.unpaginated,
  calls: calls ? calls.length : null,
  first: r.items.length ? r.items[0] : null,
  last: r.items.length ? r.items[r.items.length - 1] : null,
})

rec('page_size', mod.PAGE_SIZE)
rec('max_pages', mod.MAX_PAGES)

// 1) 跨三页拿全
{ const c = []; const r = await mod.fetchAllPages(paged(250, c)); rec('three_pages', shape(r, c)); rec('three_pages_page_size', c[0][1]); rec('three_pages_pages_arg', c.map(x => x[0])) }

// 2) 总数正好是整数页 —— 不许少拿，也不许重复累加
{ const c = []; const r = await mod.fetchAllPages(paged(200, c)); rec('exact_pages', shape(r, c)) }

// 3) 空集合
{ const c = []; const r = await mod.fetchAllPages(paged(0, c)); rec('empty', shape(r, c)) }

// 4) 单页
{ const c = []; const r = await mod.fetchAllPages(paged(30, c)); rec('single_page', shape(r, c)) }

// 5) 裸数组：该接口本来就没分页，原样返回，且**只能请求一次**
{ const c = []; const r = await mod.fetchAllPages(async (page, pageSize) => { c.push([page, pageSize]); return [7, 8, 9] })
  rec('bare_array', shape(r, c)) }

// 6) 后端一直给满页（total 撒谎 / 无穷多）—— 必须靠 maxPages 停下，不许转圈
{ const c = []; const r = await mod.fetchAllPages(async (page, pageSize) => { c.push([page, pageSize]); return { results: new Array(pageSize).fill(page) } }, { maxPages: 3 })
  rec('lies_forever', shape(r, c)) }

// 7) 真的拿不完全 —— truncated 必须为 true
{ const c = []; const r = await mod.fetchAllPages(paged(100000, c), { maxPages: 3 }); rec('truncated', shape(r, c)) }

// 8) 自定义 pageSize 要一路传下去
{ const c = []; const r = await mod.fetchAllPages(paged(20, c), { pageSize: 7 }); rec('custom_page_size', shape(r, c)); rec('custom_page_size_arg', c[0][1]) }

// 9) unwrapResults 认哪些形状
rec('unwrap', [
  mod.unwrapResults({ results: [1, 2] }).length,
  mod.unwrapResults([1, 2]).length,
  mod.unwrapResults(null).length,
  mod.unwrapResults({}).length,
  mod.unwrapResults({ results: null }).length,
])

console.log(JSON.stringify(out))
'''


def _node_can_strip_types():
    if not NODE:
        return False
    try:
        done = subprocess.run([NODE, STRIP_TYPES, '-e', '0'],
                              capture_output=True, timeout=60)
    except Exception:
        return False
    return done.returncode == 0


_NODE_OK = _node_can_strip_types()


@unittest.skipUnless(_NODE_OK, f'本机没有可用的 node {STRIP_TYPES}，整块跳过（不假装通过）')
class FetchAllPagesBehaviourTests(unittest.TestCase):
    """把 `pagination.ts` 真跑起来。类型注解由 Node 自己剥掉，不需要构建。"""

    @classmethod
    def setUpClass(cls):
        cls.result = cls._run_driver()

    @staticmethod
    def _run_driver():
        with tempfile.TemporaryDirectory() as tmp:
            driver = Path(tmp) / 'driver.mjs'
            driver.write_text(_DRIVER, encoding='utf-8')
            # 60s 是**看门狗**：循环写错的表现是永远不返回，不是报错。
            done = subprocess.run(
                [NODE, STRIP_TYPES, str(driver), HELPER.as_uri()],
                capture_output=True, timeout=60,
            )
        if done.returncode != 0:
            raise AssertionError(
                '驱动跑挂了：\n' + done.stdout.decode('utf-8', 'replace') +
                '\n' + done.stderr.decode('utf-8', 'replace')
            )
        return json.loads(done.stdout.decode('utf-8').strip().splitlines()[-1])

    def test_上限常量传到了前端(self):
        self.assertEqual(self.result['page_size'], MAX_PAGE_SIZE)
        self.assertGreater(self.result['max_pages'], 0)

    def test_跨三页拿全(self):
        got = self.result['three_pages']
        self.assertEqual(got['len'], 250)
        self.assertEqual(got['pages'], 3)
        self.assertFalse(got['truncated'])
        self.assertFalse(got['unpaginated'])
        self.assertEqual(got['first'], 0)
        self.assertEqual(got['last'], 249)
        # 页码必须是 1,2,3 —— 从 0 开始或者原地打转都会在这里露出来
        self.assertEqual(self.result['three_pages_pages_arg'], [1, 2, 3])

    def test_每页要的都是上限条数(self):
        # 防止有人「顺手」把 pageSize 写小，那样会多翻十几倍的请求
        self.assertEqual(self.result['three_pages_page_size'], MAX_PAGE_SIZE)

    def test_总数正好整数页时不多拿也不少拿(self):
        got = self.result['exact_pages']
        self.assertEqual(got['len'], 200)
        self.assertFalse(got['truncated'])

    def test_空集合(self):
        got = self.result['empty']
        self.assertEqual(got['len'], 0)
        self.assertEqual(got['pages'], 1)
        self.assertFalse(got['truncated'])

    def test_单页(self):
        got = self.result['single_page']
        self.assertEqual(got['len'], 30)
        self.assertEqual(got['pages'], 1)

    def test_裸数组的接口只请求一次(self):
        # 没分页的接口返回裸数组。要是也去翻页，同一批数据会被重复累加 50 份。
        got = self.result['bare_array']
        self.assertEqual(got['len'], 3)
        self.assertEqual(got['calls'], 1)
        self.assertTrue(got['unpaginated'])
        self.assertFalse(got['truncated'])

    def test_后端一直给满页时能停下来(self):
        # 这条是本文件存在的主要理由：终止条件写错 = 生产环境转圈。
        got = self.result['lies_forever']
        self.assertEqual(got['calls'], 3)
        self.assertEqual(got['len'], 300)
        self.assertTrue(got['truncated'])

    def test_拿不完全时_truncated_为真(self):
        got = self.result['truncated']
        self.assertTrue(got['truncated'])
        self.assertEqual(got['len'], 300)

    def test_自定义_page_size_一路传下去(self):
        got = self.result['custom_page_size']
        self.assertEqual(self.result['custom_page_size_arg'], 7)
        self.assertEqual(got['len'], 20)
        self.assertEqual(got['pages'], 3)

    def test_unwrapResults_认的三种形状(self):
        results, bare, nul, empty_obj, null_results = self.result['unwrap']
        self.assertEqual((results, bare), (2, 2))
        self.assertEqual((nul, empty_obj, null_results), (0, 0, 0))


if __name__ == '__main__':
    unittest.main(verbosity=2)
