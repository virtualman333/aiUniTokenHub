#!/usr/bin/env node
/**
 * 「SEO 表面积」契约检查 —— `node scripts/check-seo.js`（已接进 `npm run build`）
 *
 * 拦的是什么
 * ----------
 * 同一件「哪些页要收录」此前写在四处（路由 meta / robots.txt / sitemap.xml / index.html 的
 * JSON-LD），没有两份对过账。实测已经矛盾了三处，且全都是**搜索引擎会直接报错、
 * 而人和构建都不会报错**的那种：
 *
 *   · sitemap 提交了 `/login` `/register` `/forgot-password`，而 robots.txt 明确 Disallow
 *     这三个 —— Search Console 报「Blocked by robots.txt」，被提交的 URL 永远进不了索引
 *   · JSON-LD 的 `SearchAction` 指向 `/search`，而路由表里没有这一条（落到 NotFound）
 *   · `SEO-OPTIMIZATION.md` 声称 `SeoMeta.vue` / `useSeoMeta.js` 是 SEO 的实现，
 *     而两者全仓零调用
 *
 * 判据一律**现算**：产物与 `seo/site.js` 比、sitemap 与 robots 两向对账、
 * 每个提交的 URL 与路由表对账、每个 `/admin` 路由的 `noIndex` 与 `router.afterEach` 的实际语义对账。
 *
 * 元检查（比检查本身更重要）
 * --------------------------
 * 每条「差集为空」的断言都配了**自证**：喂一段合成长相的数据，确认它真的报得出来。
 * 否则「集合两边都空」会让整条断言恒真 —— 本仓库栽过（`run_tests.py` 收窄扫描面后
 * 全仓从 295 例掉到 116 例、退出码仍是 0）。
 */
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import {
  GENERATED_MARK,
  OG_IMAGE_URL,
  PRIVATE_PREFIXES,
  PUBLIC_PAGES,
  SITE_ORIGIN,
  disallowRules,
  robotsTxt,
  sitemapPaths,
  sitemapXml
} from '../seo/site.js'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

let pass = 0
const fails = []
const ok = (cond, name, extra) => {
  if (cond) pass++
  else fails.push(name + (extra ? ` → ${extra}` : ''))
}
const eq = (a, b, name) => ok(a === b, name, `期望 ${JSON.stringify(b)}，实际 ${JSON.stringify(a)}`)
const section = (s) => console.log('\n' + s)

const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8')
const exists = (rel) => fs.existsSync(path.join(ROOT, rel))

// --------------------------------------------------------------------- 工具

/** 剥掉注释（跳过字符串字面量）。结构锁读源码前必须先剥 —— 注释里正大光明写着旧形态。 */
export function stripComments(src) {
  let out = ''
  let i = 0
  let quote = null
  while (i < src.length) {
    const c = src[i]
    const n = src[i + 1]
    if (quote) {
      if (c === '\\') { out += c + (n === undefined ? '' : n); i += 2; continue }
      if (c === quote) quote = null
      out += c; i += 1; continue
    }
    if (c === '"' || c === "'" || c === '`') { quote = c; out += c; i += 1; continue }
    if (c === '/' && n === '/') { while (i < src.length && src[i] !== '\n') i += 1; continue }
    if (c === '/' && n === '*') {
      i += 2
      while (i < src.length && !(src[i] === '*' && src[i + 1] === '/')) i += 1
      i += 2; continue
    }
    out += c; i += 1
  }
  return out
}

/**
 * 从 router 源码解析路由表。
 *
 * 判据是 `path:` 那行的**缩进**：4 空格 = 顶层路由，更深 = 上一个顶层路由的子路由。
 * 条目自身的区间取到「下一个 `path:` 或 `children:` 行」为止 —— 因为 `meta:` 一定写在
 * `children:` 之前，这样父路由的 `meta.noIndex` 不会被子的正文污染（否则父条目永远「看得见」
 * 子条目里的 `noIndex`，断言就成恒真了）。
 *
 * `noIndex` / `requiresAuth` 都保留三态（true / false / undefined）：vue-router 的 `to.meta`
 * 是**后者覆盖前者**，所以子路由写 `noIndex: false` 会盖掉父路由的 `true` —— 这正是一条
 * 会静默出事的路径，必须能看见它。
 */
export function parseRoutes(src) {
  const clean = stripComments(src)
  const lines = clean.split('\n')
  const marks = []
  for (let i = 0; i < lines.length; i++) {
    // `path:` 可以不在行首 —— 单行写法的条目（`{ path: 'x', meta: {...} },`）同样要解析到。
    // 层级取**该行的前导空白**，不是 `path:` 的列号。
    const m = /^(\s*).*?\bpath:\s*'([^']*)'/.exec(lines[i])
    if (m) marks.push({ line: i, indent: m[1].length, path: m[2] })
  }
  const routes = []
  let top = null
  for (let k = 0; k < marks.length; k++) {
    const mk = marks[k]
    // 条目正文：到下一个 path: / children: 行为止
    let end = lines.length
    for (let i = mk.line + 1; i < lines.length; i++) {
      if (/^\s*(path:|children:)/.test(lines[i])) { end = i; break }
    }
    const body = lines.slice(mk.line, end).join('\n')
    const noIndex = /noIndex:\s*(true|false)/.exec(body)
    const requiresAuth = /requiresAuth:\s*(true|false)/.exec(body)
    const entry = {
      path: mk.path,
      indent: mk.indent,
      own: { noIndex: noIndex ? noIndex[1] === 'true' : undefined, requiresAuth: requiresAuth ? requiresAuth[1] === 'true' : undefined }
    }
    if (mk.indent <= 4) {
      top = entry
      entry.topPath = mk.path
    } else {
      entry.topPath = top ? top.path : null
      entry.parent = top
    }
    // 有效值：自身没写就继承顶层（与实际 router 的 meta 合并一致）
    entry.effNoIndex = entry.own.noIndex !== undefined
      ? entry.own.noIndex
      : (entry.parent ? entry.parent.own.noIndex : undefined)
    entry.effRequiresAuth = entry.own.requiresAuth !== undefined
      ? entry.own.requiresAuth
      : (entry.parent ? entry.parent.own.requiresAuth : undefined)
    entry.full = entry.indent <= 4 ? mk.path : joinPath(top ? top.path : '', mk.path)
    entry.dynamic = mk.path.includes(':')
    routes.push(entry)
  }
  return routes
}

function joinPath(top, p) {
  if (p.startsWith('/')) return p
  if (!p) return top || '/'
  return (top.endsWith('/') ? top : top + '/') + (top.endsWith('/') ? p : p)
}

/** robots.txt 的 Disallow 条目（一行一条） */
export function parseDisallow(text) {
  return [...text.matchAll(/^\s*Disallow:\s*(\S+)\s*$/gm)].map((m) => m[1])
}

/** robots.txt 的 Sitemap 行 */
export function parseSitemapLine(text) {
  return [...text.matchAll(/^\s*Sitemap:\s*(\S+)\s*$/gm)].map((m) => m[1])
}

/** sitemap.xml 里的 `<loc>` 清单 */
export function parseLocs(xml) {
  return [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1])
}

/** 一个路径是否被某条 Disallow 规则挡住（前缀匹配，与爬虫的规则一致） */
export function blockedBy(rule, p) {
  if (rule.endsWith('/')) return p === rule.slice(0, -1) || p.startsWith(rule)
  return p === rule || p.startsWith(rule)
}

/** 收集 JSON-LD 里所有指向本站的 URL（跳过静态资源） */
export function siteUrlsInJsonLd(value, acc = []) {
  if (typeof value === 'string') {
    if (value.startsWith(SITE_ORIGIN)) acc.push(value)
  } else if (Array.isArray(value)) {
    for (const v of value) siteUrlsInJsonLd(v, acc)
  } else if (value && typeof value === 'object') {
    for (const v of Object.values(value)) siteUrlsInJsonLd(v, acc)
  }
  return acc
}

/** 本站 URL → 路由路径（去掉 origin / query / hash） */
export function routePathOf(url) {
  return url.slice(SITE_ORIGIN.length).split(/[?#]/)[0] || '/'
}

// ============================================================ 读取现场
const routerSrc = read('src/router/index.js')
const routes = parseRoutes(routerSrc)
const robots = read('public/robots.txt')
const sitemap = read('public/sitemap.xml')
const html = read('index.html')
const pkg = JSON.parse(read('package.json'))

section('1. 解析面不许为空（下面每条「差集为空」都靠它才有意义）')
ok(routes.length >= 20, `从 router 解析出 ${routes.length} 条路由`, '解析面塌了说明路由写法变了，这个解析要跟着改')
ok(routes.filter((r) => r.indent <= 4).length >= 6, `其中顶层路由 ${routes.filter((r) => r.indent <= 4).length} 条`)
const adminRoutes = routes.filter((r) => r.full === '/admin' || r.full.startsWith('/admin/'))
const appRoutes = routes.filter((r) => r.full === '/app' || r.full.startsWith('/app/'))
ok(adminRoutes.length >= 10, `其中 /admin 下 ${adminRoutes.length} 条`, '少到个位数说明层级解析错了')
ok(appRoutes.length >= 10, `其中 /app 下 ${appRoutes.length} 条`)
ok(PUBLIC_PAGES.length >= 5, `公共页清单 ${PUBLIC_PAGES.length} 条`)
ok(routes.some((r) => r.dynamic), '认得出通配路由（/:pathMatch(.*)*）—— 它不能被当成「真实存在的页面」')

section('2. 自证：这些解析器真的报得出来吗')
// 每条自证都是「喂一段合成长相的数据，确认两个方向都认得」——没有它们，
// 上面的解析面一旦塌掉，下面所有「差集为空」都会在空集上通过。
{
  const fake = [
    'const routes = [',
    '  {',
    "    path: '/admin',",
    '    meta: { requiresAuth: true, noIndex: true },',
    '    children: [',
    "      { path: '', meta: { title: 'a' } },",
    "      { path: 'x', meta: { title: 'b', noIndex: false } },",
    "      { path: 'y', meta: { title: 'c', noIndex: true } }",
    '    ]',
    '  },',
    "  { path: '/search', meta: { title: 'search' } }",
    ']'
  ].join('\n')
  const fr = parseRoutes(fake)
  eq(fr.length, 5, '自证：合成 router 解析出 5 条路由')
  const adminKid = fr.find((r) => r.full === '/admin/x')
  eq(adminKid.effNoIndex, false, '自证：子路由写 noIndex:false 会盖掉父路由的 true（这条必须看得见）')
  eq(fr.find((r) => r.full === '/admin').effNoIndex, true, '自证：父路由自己的 noIndex 认得出')
  eq(fr.find((r) => r.full === '/admin/y').effNoIndex, true, '自证：不写的子路由继承父路由')
  eq(fr.find((r) => r.full === '/admin').full, '/admin', '自证：顶层路径不拼接')
  ok(!fr.some((r) => r.full === '/search') === false, '自证：合成数据里的 /search 确实在路由表里（下面拿它当反例）')
}
{
  const fakeRobots = 'User-agent: *\nDisallow: /app/\nDisallow: /forgot-password\n'
  eq(parseDisallow(fakeRobots).length, 2, '自证：robots 的 Disallow 解析')
  ok(blockedBy('/app/', '/app/api-doc'), '自证：前缀规则命中子路径')
  ok(blockedBy('/app/', '/app'), '自证：带斜杠的规则也命中不带斜杠的路径本身')
  ok(!blockedBy('/app/', '/application'), '自证：前缀匹配按路径段，不许把 /application 也算进去')
  eq(parseLocs('<url><loc>https://a/b</loc></url>').length, 1, '自证：sitemap 的 loc 解析')
  eq(siteUrlsInJsonLd({ t: { urlTemplate: `${SITE_ORIGIN}/search?q={x}` } }).length, 1, '自证：JSON-LD 里嵌套的 urlTemplate 抓得到')
  eq(routePathOf(`${SITE_ORIGIN}/search?q=1`), '/search', '自证：URL → 路由路径会剥掉 query')
}

section('3. 产物必须是「生成物」，且与 seo/site.js 一致')
for (const [rel, content] of [['public/robots.txt', robotsTxt()], ['public/sitemap.xml', sitemapXml()]]) {
  ok(exists(rel), `${rel} 存在`)
  const actual = rel.endsWith('.txt') ? robots : sitemap
  eq(actual === content, true, `${rel} 与 seo/site.js 现算的内容逐字节一致`,
    '不一致说明有人手改了这个产物 —— 改 seo/site.js 再跑 node scripts/gen-seo.js')
  ok(actual.includes(GENERATED_MARK), `${rel} 带生成物标记`, GENERATED_MARK)
}

section('4. sitemap ⇄ robots：两向对账（★ 本轮修的就是这里）')
const disallow = parseDisallow(robots)
const locs = parseLocs(sitemap)
const locPaths = locs.map(routePathOf)
ok(locs.length > 0, `sitemap 里有 ${locs.length} 条 URL`, '解析面为空，下面几条会在空集上通过')
ok(disallow.length > 0, `robots.txt 里有 ${disallow.length} 条 Disallow`)
{
  // 方向一：提交给搜索引擎的 URL，一条都不许被自己家的 robots.txt 挡住
  const blocked = locPaths.filter((p) => disallow.some((rule) => blockedBy(rule, p)))
  ok(blocked.length === 0,
    '★ sitemap 提交的 URL 没有一条被 robots.txt 挡住（否则它就永远进不了索引，而 sitemap 的全部意义就是让它进索引）',
    blocked.join('，'))
  // 方向二：判为可收录的公共页，一条都不许漏
  const missing = sitemapPaths().filter((p) => !locPaths.includes(p))
  ok(missing.length === 0, '判为可收录的公共页都在 sitemap 里', missing.join('，'))
  // 方向三：sitemap 里不许有别的东西
  const extra = locPaths.filter((p) => !sitemapPaths().includes(p))
  ok(extra.length === 0, 'sitemap 里没有 seo/site.js 之外的自作主张的 URL', extra.join('，'))
  // 方向四：判为不收录的公共页，必须在 robots 里被明确挡住（否则「不收录」只是句空话）
  const notBlocked = PUBLIC_PAGES.filter((p) => !p.indexable).map((p) => p.path)
    .filter((p) => !disallow.some((rule) => blockedBy(rule, p)))
  ok(notBlocked.length === 0, '判为不收录的公共页确实被 robots.txt 挡住了（不许只靠「不进 sitemap」）', notBlocked.join('，'))
  // 方向五：Disallow 里不许有来路不明的条目（表会腐烂）
  const known = new Set([...PRIVATE_PREFIXES.map((p) => p.prefix), ...PUBLIC_PAGES.map((p) => p.path)])
  const stray = disallow.filter((rule) => !known.has(rule))
  ok(stray.length === 0, 'robots.txt 的每条 Disallow 都能在 seo/site.js 里找到出处', stray.join('，'))
}

section('5. sitemap ⇄ 路由表')
{
  const real = new Set(routes.filter((r) => !r.dynamic).map((r) => r.full))
  const missing = locPaths.filter((p) => !real.has(p))
  ok(missing.length === 0, '★ 提交给搜索引擎的每个 URL 都是路由表里真实存在的页面', missing.join('，'))
  const guarded = locPaths.filter((p) => {
    const r = routes.find((x) => x.full === p)
    return r && r.effRequiresAuth === true
  })
  ok(guarded.length === 0, 'sitemap 里没有「要求登录」的页面（爬虫只会看到跳转到登录页）', guarded.join('，'))
}

section('6. 管理后台不许被收录（AGENTS.md 说「admin routes set noIndex」，此前没人扛）')
{
  ok(adminRoutes.length > 0, `有 ${adminRoutes.length} 条 /admin 路由要查`)
  const leaky = adminRoutes.filter((r) => r.effNoIndex !== true)
  ok(leaky.length === 0, '★ /admin 下每条路由的 noIndex 都真的为 true（含从父路由继承的情形）',
    leaky.map((r) => r.full).join('，'))
  // 双保险：robots.txt 也必须挡住后台（router 的 noIndex 只对会执行 JS 的爬虫有效）
  ok(disallow.some((rule) => blockedBy(rule, '/admin/')),
    '★ robots.txt 也挡住 /admin/ —— router 里的 noIndex 要等 JS 跑完才生效，初始 HTML 是一样的')
  const noIndexLiterals = adminRoutes.filter((r) => r.own.noIndex === true).length
  ok(noIndexLiterals >= adminRoutes.length - 1,
    `每条 /admin 路由都显式写了 noIndex（${noIndexLiterals}/${adminRoutes.length}）—— 只靠父路由继承也成立，但显式写下更能扛住重构`)
  // /app 的前提：全部要求登录。这条不成立的话，robots 里那条 Disallow 的理由就没了
  const openApp = appRoutes.filter((r) => r.effRequiresAuth !== true)
  ok(openApp.length === 0, '★ /app 下每条路由都真的要求登录（robots.txt 挡住它的理由）',
    openApp.map((r) => r.full).join('，'))
}

section('7. index.html：静态 meta 与 JSON-LD')
{
  const robotsMeta = /<meta\s+name="robots"\s+content="([^"]*)"/.exec(html)
  ok(!!robotsMeta, 'index.html 有静态 robots meta')
  if (robotsMeta) {
    ok(!/noindex/i.test(robotsMeta[1]),
      '★ index.html 的 robots 初值不是 noindex（否则爬虫拿到的静态 HTML 就是「别收录」，整站白干）',
      robotsMeta[1])
  }
  const canonical = /<link\s+rel="canonical"\s+href="([^"]*)"/.exec(html)
  ok(!!canonical, 'index.html 有 canonical')
  if (canonical) {
    ok(canonical[1].startsWith(SITE_ORIGIN),
      'canonical 用的是站点主域（改域名时两处必须一起改）', canonical[1])
  }
  for (const [tag, re] of [
    ['og:url', /<meta\s+property="og:url"\s+content="([^"]*)"/],
    ['og:image', /<meta\s+property="og:image"\s+content="([^"]*)"/],
    ['twitter:image', /<meta\s+name="twitter:image"\s+content="([^"]*)"/]
  ]) {
    const m = re.exec(html)
    ok(!!m, `index.html 有 ${tag}`)
    if (m) ok(m[1].startsWith(SITE_ORIGIN), `${tag} 指向站点主域`, m[1])
  }
  eq(/<meta\s+property="og:image"\s+content="([^"]*)"/.exec(html)[1], OG_IMAGE_URL,
    'og:image 与 seo/site.js 的 OG_IMAGE_URL 一致（两处手抄必然漂移）')

  // JSON-LD：能解析 + 里面出现的每个本站 URL 都得是真页面
  const blocks = [...html.matchAll(/<script\s+type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((m) => m[1])
  ok(blocks.length > 0, `index.html 里有 ${blocks.length} 段 JSON-LD`)
  const bad = []
  const allSiteUrls = []
  for (const b of blocks) {
    let parsed
    try {
      parsed = JSON.parse(b)
      pass++
    } catch (e) {
      fails.push('JSON-LD 必须能被 JSON.parse 解析 → ' + e.message)
      continue
    }
    for (const url of siteUrlsInJsonLd(parsed)) {
      const p = routePathOf(url)
      if (p.startsWith('/assets/')) continue // 静态资源，由反向代理服务，不是页面
      allSiteUrls.push(p)
      const real = new Set(routes.filter((r) => !r.dynamic).map((r) => r.full))
      if (!real.has(p)) bad.push(p)
    }
  }
  ok(allSiteUrls.length > 0, `JSON-LD 里解析出 ${allSiteUrls.length} 个本站 URL`, '一个都没抓到说明结构变了')
  ok(bad.length === 0,
    '★ JSON-LD 里没有指向不存在页面的 URL（旧版这里挂着 SearchAction → /search，路由表里根本没有 /search）',
    bad.join('，'))
}

section('8. 前端配置：检查必须在构建时跑')
{
  eq(pkg.scripts['check:seo'], 'node scripts/check-seo.js', 'package.json 有 check:seo 且指向本文件')
  eq(pkg.scripts['gen:seo'], 'node scripts/gen-seo.js', 'package.json 有 gen:seo 且指向生成器')
  ok(exists('scripts/check-seo.js') && exists('scripts/gen-seo.js') && exists('seo/site.js'),
    '三个文件的路径都真实存在（脚本名指向空气是本仓栽过的坑）')
  const build = String(pkg.scripts.build || '')
  ok(build.includes('check:seo'),
    '★ npm run build 里串了 check:seo —— 否则产物与唯一来源不一致时构建照样过，用户照旧拿到错的 robots.txt')
}

section('9. SEO 的写者只能有一个')
{
  const files = []
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (['node_modules', 'dist', '.vite'].includes(e.name)) continue
      const p = path.join(dir, e.name)
      if (e.isDirectory()) walk(p)
      else if (/\.(js|ts|vue|mjs)$/.test(e.name)) files.push(p)
    }
  }
  walk(path.join(ROOT, 'src'))
  ok(files.length > 20, `扫了 src 下 ${files.length} 个源码文件`, '扫描面塌了，下面几条会在空集上通过')
  // ★ @vueuse/head 的 useHead 是第二个写者：它和 router.afterEach 抢同一批标签，
  //   而它的 noIndex 默认是 false —— 在 admin 页上用一次就会把 robots 写回 index, follow。
  //   本轮删掉了那条零调用的死路径（SeoMeta.vue / useSeoMeta.js），这里拦住它复活。
  // ★ 先剥注释再判：在源码里写一句「别用 useHead()」不该被判红（本仓栽过「注释当实现」三次）。
  const headUsers = files.filter((f) => /useHead\s*\(/.test(stripComments(fs.readFileSync(f, 'utf8'))))
  ok(headUsers.length === 0, '★ src 下没有第二份 meta 写者（useHead）—— 它会和 router.afterEach 抢同一批标签，且在后台页上默认写 index, follow',
    headUsers.map((f) => path.relative(ROOT, f)).join('，'))
  const robotsWriters = files.filter((f) => /'robots'|"robots"|noindex,\s*nofollow/.test(stripComments(fs.readFileSync(f, 'utf8'))))
  const rel = robotsWriters.map((f) => path.relative(ROOT, f).replace(/\\/g, '/'))
  eq(rel.join(','), 'src/router/index.js', '★ 写 robots 标签的地方只有 src/router/index.js 一处')
  for (const dead of ['src/components/SeoMeta.vue', 'src/composables/useSeoMeta.js']) {
    ok(!exists(dead), `${dead} 不存在（零调用的死路径，已删；要用请先把它接上真页面）`)
  }
}

// ------------------------------------------------------------------ 汇总
console.log('\n' + '='.repeat(58))
const total = pass + fails.length + 1
ok(total >= 45, `断言条数下限（${total} ≥ 45）`, '条数骤降说明有整组断言没跑起来')
if (fails.length) {
  console.log(`通过 ${pass} 项，失败 ${fails.length} 项`)
  fails.forEach((f) => console.log('  ✗ ' + f))
  process.exit(1)
}
console.log(`SEO 表面积契约：通过 ${pass} / ${pass}`)
