# -*- coding: utf-8 -*-
"""SEO 表面积契约的**落点** —— 检查在前端（Node），这里保证它「真的存在、真的会跑、跑了要绿」。

为什么要这个文件
----------------
`frontend/scripts/check-seo.js` 是这一轮的实质检查：产物必须是生成物、sitemap 与
robots.txt 两向对账、提交的每个 URL 都要在路由表里、`/admin` 下每条路由的 `noIndex`
都要为真、JSON-LD 里不许指向不存在的页面。

但它同时落在两个「没有人跑」的盲区里：

  1. **前端没有任何测试/校验入口**（AGENTS.md 原话：「There are no configured frontend
     lint/test/typecheck scripts」）。一个只存在于 `frontend/` 的检查脚本，不加接线就是
     「写下来没人跑」的东西 —— 本仓对这类东西的处理是**要么接进入口、要么删掉**。
  2. `npm run build` 里串了它（这是它唯一的自动触发点），但「build 里到底串没串」
     本身没人看。有人把 build 改回 `vite build && node scripts/zip-dist.js` 之后，
     所有断言还是绿的，而错版 sitemap 会照旧发出去。

所以这一层只管三件事，**不重复实现任何判据**（判据在 Node 侧，这里重复一份就是又开了
一个会漂移的事实）：

  · 三个入口文件、两个 npm script、`build` 的接线 —— 都在；
  · 产物带着生成物标记（手改过的产物没有这个标记）；
  · **真的执行** `node scripts/check-seo.js`，要求退出码 0 **且**输出里带得出断言条数
    （防止「脚本被改成了空跑」这种最坏情况：退出码 0、什么都没查）。

顺带锁一条文档漂移：那两个被删掉的死文件（`SeoMeta` 组件与 `useSeoMeta` composable）
不许在文档里以**路径**的形式重新出现 —— 它们是「文档声称已完成、代码里零调用」的样本，
留着路径就等于留着一条会把人引到空地上的指示。

本机没有 node 时整块 skip，**不假装通过**。
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
REPO = BACKEND.parent
FRONTEND = REPO / 'frontend'

CHECK = FRONTEND / 'scripts' / 'check-seo.js'
GEN = FRONTEND / 'scripts' / 'gen-seo.js'
SOURCE = FRONTEND / 'seo' / 'site.js'
PACKAGE = FRONTEND / 'package.json'
ROBOTS = FRONTEND / 'public' / 'robots.txt'
SITEMAP = FRONTEND / 'public' / 'sitemap.xml'

#: 断言条数下限 —— 脚本被改成空跑时，这条是唯一能发现它的东西
MIN_ASSERTIONS = 45

#: 生成物标记（`seo/site.js` 的 `GENERATED_MARK`）。两处写法必须一致 ——
#: 这里刻意**手写**这个字符串而不是从 JS 里读：从被测对象里读期望值，
#: 改掉被测对象它也跟着改，那是恒真。
GENERATED_MARK = 'GENERATED-BY scripts/gen-seo.js'

NODE = shutil.which('node')


def _frontend_scripts():
    return json.loads(PACKAGE.read_text(encoding='utf-8')).get('scripts', {})


class SeoCheckHasALandingPlace(unittest.TestCase):
    """检查脚本本身有没有落点。"""

    def test_三个入口文件都在(self):
        for f in (CHECK, GEN, SOURCE):
            self.assertTrue(f.is_file(), f'{f.relative_to(REPO)} 不存在 —— 检查的落点没了')

    def test_npm_script_指的正是这两个文件(self):
        scripts = _frontend_scripts()
        self.assertEqual(scripts.get('check:seo'), 'node scripts/check-seo.js')
        self.assertEqual(scripts.get('gen:seo'), 'node scripts/gen-seo.js')

    def test_构建时必跑(self):
        """`npm run build` 是 AGENTS.md 指定的前端冒烟检查 —— SEO 契约挂在它上面。"""
        build = _frontend_scripts().get('build', '')
        self.assertIn('check:seo', build,
                      'build 里没有串 check:seo：产物与唯一来源不一致时构建照样会过')

    def test_产物带生成物标记(self):
        """手改过的产物不会有这个标记 —— 这一条就是「它是不是生成物」的判据。"""
        for f in (ROBOTS, SITEMAP):
            self.assertTrue(f.is_file(), f'{f.relative_to(REPO)} 不存在')
            text = f.read_text(encoding='utf-8')
            self.assertIn(GENERATED_MARK, text,
                          f'{f.relative_to(REPO)} 不带生成物标记，像是手改的')
            self.assertIn('seo/site.js', text,
                          f'{f.relative_to(REPO)} 没说明唯一来源在哪，改的人会去改它本身')


class SeoCheckActuallyRuns(unittest.TestCase):
    """不是「读代码看着没问题」，而是真执行一遍。"""

    def test_检查脚本真跑起来并且绿(self):
        if not NODE:
            self.skipTest('本机没有 node，整块跳过（不假装通过）')
        done = subprocess.run(
            [NODE, 'scripts/check-seo.js'],
            cwd=str(FRONTEND), capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        out = (done.stdout or '') + (done.stderr or '')
        self.assertEqual(done.returncode, 0, f'check-seo.js 退出码 {done.returncode}\n{out}')
        m = re.search(r'通过 (\d+) / (\d+)', out)
        self.assertIsNotNone(m, f'输出里没有断言条数 —— 它可能被改成空跑了\n{out}')
        passed, total = int(m.group(1)), int(m.group(2))
        self.assertEqual(passed, total, f'内部计数不自洽：{out}')
        self.assertGreaterEqual(total, MIN_ASSERTIONS,
                                f'只有 {total} 条断言（下限 {MIN_ASSERTIONS}）—— 有整组检查没跑起来\n{out}')

    def test_生成器是幂等的(self):
        """`gen-seo.js --check` 不写盘、只比对；产物最新时退出码 0。

        这条同时钉住「产物与 seo/site.js 一致」—— 手改产物之后它会红。
        """
        if not NODE:
            self.skipTest('本机没有 node，整块跳过（不假装通过）')
        done = subprocess.run(
            [NODE, 'scripts/gen-seo.js', '--check'],
            cwd=str(FRONTEND), capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        out = (done.stdout or '') + (done.stderr or '')
        self.assertEqual(
            done.returncode, 0,
            '产物与 seo/site.js 不一致（有人手改了 robots.txt / sitemap.xml？）\n' + out
        )
        self.assertIn('一致', out, out)


class DeletedSeoPathsStayDeleted(unittest.TestCase):
    """两个「文档声称已完成、代码里零调用」的文件已被删除。

    锁的是**文档里的路径**，不是名字：它们在文档里作为历史被提到是可以的，
    但不能再以 `src/...` 的形式出现 —— 那会把下一个读文档的人引到空地上。
    """

    DOCS = (REPO / 'AGENTS.md', REPO / 'README.md', FRONTEND / 'SEO-OPTIMIZATION.md',
            BACKEND / 'README.md')
    DEAD_PATHS = ('src/components/SeoMeta', 'src/composables/useSeoMeta', '@/components/SeoMeta',
                  '@/composables/useSeoMeta')

    def test_死路径不许在文档里复活(self):
        offenders = []
        for doc in self.DOCS:
            if not doc.is_file():
                continue
            text = doc.read_text(encoding='utf-8')
            for p in self.DEAD_PATHS:
                if p in text:
                    offenders.append(f'{doc.relative_to(REPO)}: {p}')
        self.assertEqual(offenders, [],
                         '文档里还写着已经删掉的 SEO 路径 —— 文档说它存在，代码里查不到：' + str(offenders))

    def test_死文件确实已经不在(self):
        for rel in ('src/components/SeoMeta.vue', 'src/composables/useSeoMeta.js'):
            self.assertFalse((FRONTEND / rel).exists(), f'{rel} 又回来了？')


if __name__ == '__main__':
    unittest.main()
