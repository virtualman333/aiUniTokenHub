/**
 * 站点的「SEO 表面积」—— **唯一来源**
 *
 * 为什么要有这个文件
 * ------------------
 * 在这之前，同一件事写在**四份互不知情的手抄件**里：
 *
 *   · `src/router/index.js`  —— 路由清单 + 每页的 `meta.noIndex`（15 处手写 `noIndex: true`）
 *   · `public/robots.txt`    —— 允许 / 禁止爬取的路径
 *   · `public/sitemap.xml`   —— 提交给搜索引擎的公共 URL
 *   · `index.html`           —— 静态 meta + 三段 JSON-LD（其中 `SearchAction` 指向 `/search`）
 *
 * 四份里没有任何两份是对过账的，于是必然互相矛盾。实测已经矛盾了三处：
 *
 *   1. `robots.txt` 写 `Disallow: /login` / `/register` / `/forgot-password`，
 *      而 `sitemap.xml` 正把这三个 URL 当「公共页面」提交（`/login`、`/register` 的
 *      priority 还是 0.8）。Search Console 对这种提交会直接报
 *      「Blocked by robots.txt」—— **被提交的 URL 永远进不了索引**，
 *      而 sitemap 存在的唯一目的就是让它们进索引。
 *   2. `index.html` 的 JSON-LD 里 `SearchAction.target` 指向
 *      `https://unitokenhub.m3it.cn/search?q={search_term_string}`，
 *      而路由表里**没有 `/search`**（会落到 `/:pathMatch(.*)*` → NotFound）。
 *      给搜索引擎提交一个指向 404 的站内搜索框。
 *   3. `SEO-OPTIMIZATION.md` 把「已完成」写在了两件不存在的事上：
 *      `SeoMeta.vue` 与 `useSeoMeta.js` 全仓**零调用**（本轮删掉），
 *      而真正在干活的 `router.afterEach` 在文档里根本没被提。
 *
 * 现在：**「某一页要不要被收录」只由下面那个 `indexable` 布尔决定**，
 * 它同时推导出 sitemap 与 robots 两侧 —— 二者再也不可能各说各话。
 * `scripts/gen-seo.js` 按本文件写产物，`scripts/check-seo.js` 逐字节比对，
 * 并额外核对路由表与 index.html。
 *
 * 为什么要去掉 `<lastmod>`
 * ------------------------
 * 旧的 sitemap 里六条 URL 的 `<lastmod>` 全是同一个 `2026-05-09` —— 四个月前随手写的，
 * 之后再没人维护过（期间站点发过 v1.1.0 / v1.2.0 / v1.3.0）。Google 对 `lastmod` 的口径是
 * 「一致且可验证才用」：一个明显失真的日期只会被忽略，甚至让整份 sitemap 的可信度打折。
 * **没有 lastmod 比一个假的 lastmod 好**，所以这里不放。
 * （`changefreq` / `priority` 保留 —— 它们是作者逐页挑的值，现在也收敛到了这一处。）
 */
'use strict'

/** 站点主域（canonical / og:url / sitemap 的 loc 一律用它拼） */
export const SITE_ORIGIN = 'https://unitokenhub.m3it.cn'

/**
 * 社交分享图。**不在前端产物里**：`/assets/` 由反向代理直接服务（favicon 也走那里），
 * 所以本仓库里查不到它是正常的，不做存在性断言 —— 只核对域名。
 */
export const OG_IMAGE_URL = `${SITE_ORIGIN}/assets/images/og-image.png`

/**
 * 公共页面 —— 未登录也能访问的那些（对应 router 里的 `guest: true` 或纯静态页）。
 *
 * `indexable` 是**产品决定**，一行一个：
 *   · true  → 进 sitemap，robots.txt 不挡它
 *   · false → 不进 sitemap，robots.txt 明确 Disallow 它
 *
 * 改这一列就等于改了收录范围，不需要再去动 robots.txt / sitemap.xml（它们是生成物）。
 */
export const PUBLIC_PAGES = [
  {
    path: '/',
    label: '首页',
    indexable: true,
    changefreq: 'weekly',
    priority: '1.0'
  },
  {
    path: '/login',
    label: '登录',
    indexable: true,
    changefreq: 'monthly',
    priority: '0.8',
    note: '品牌词检索的落地页。旧 robots.txt 挡了它、旧 sitemap 又按 0.8 提交它，两边打架；'
      + '这里按 sitemap 的意图放行。要改回不收录，把 indexable 改成 false 就行'
  },
  {
    path: '/register',
    label: '注册',
    indexable: true,
    changefreq: 'monthly',
    priority: '0.8',
    note: '转化页，与登录页同理'
  },
  {
    path: '/forgot-password',
    label: '忘记密码',
    indexable: false,
    changefreq: 'yearly',
    priority: '0.3',
    note: '找回密码流程的入口。收录它没有检索价值，只会引来「重置密码」类垃圾流量。'
      + '旧 sitemap 把它也按 0.3 提交了，与 robots.txt 的 Disallow 直接矛盾 —— 这里判不收录'
  },
  {
    path: '/privacy-policy',
    label: '隐私政策',
    indexable: true,
    changefreq: 'yearly',
    priority: '0.5'
  },
  {
    path: '/terms-of-service',
    label: '用户协议',
    indexable: true,
    changefreq: 'yearly',
    priority: '0.5'
  }
]

/**
 * 不许爬取的前缀 —— 与「公共页面」互补的那一半。
 *
 * `/app/` 之所以整条挡掉：用户端所有页面在 router 里都继承 `/app` 父路由的
 * `requiresAuth: true`，爬虫拿到的是重定向到 `/login` —— 收录它只会得到一堆
 * 内容相同的空壳。`/app/api-doc`、`/app/model-square` 这些本该有 SEO 价值的页面
 * 也在同一个前提里；**要让它们可收录，得先让它们不要求登录，而不是改 robots。**
 */
export const PRIVATE_PREFIXES = [
  { prefix: '/admin/', note: '管理后台（router 里全部 noIndex，双保险）' },
  { prefix: '/app/', note: '用户端全部要求登录（router 继承 requiresAuth: true）' }
]

/**
 * 会进 sitemap 的**页面对象** —— `sitemapPaths()` 与 `sitemapXml()` 都从这里取。
 *
 * ⚠ 这个函数存在的原因是负向验证撞出来的：这两处本来各写了一遍
 * `PUBLIC_PAGES.filter(p => p.indexable)`，于是把其中一个改坏（比如让它忽略 `indexable`）
 * 之后，「检查用的路径清单」与「生成器写出来的清单」当场分叉 ——
 * 正是本仓反复出现的「同一件事写两遍」。筛选只此一处。
 */
export function sitemapPages() {
  return PUBLIC_PAGES.filter((p) => p.indexable)
}

/** 会写进 sitemap 的路径（顺序即 sitemap 里的顺序） */
export function sitemapPaths() {
  return sitemapPages().map((p) => p.path)
}

/** 会写进 robots.txt 的 Disallow 条目 */
export function disallowRules() {
  return [
    ...PRIVATE_PREFIXES.map((p) => p.prefix),
    ...PUBLIC_PAGES.filter((p) => !p.indexable).map((p) => p.path)
  ]
}

/** 产物头部标记 —— `check-seo.js` 靠它确认这两个文件是生成物、不是手改的 */
export const GENERATED_MARK = 'GENERATED-BY scripts/gen-seo.js'

/** robots.txt 的正文（`gen-seo.js` 落盘，`check-seo.js` 逐字节比对） */
export function robotsTxt() {
  const lines = [
    `# ${GENERATED_MARK} —— 内容来自 seo/site.js`,
    '# 改收录范围请改 seo/site.js 里的 PUBLIC_PAGES / PRIVATE_PREFIXES，不要手改本文件',
    '',
    '# https://www.robotstxt.org/robotstxt.html',
    '# 本文件控制搜索引擎爬虫对网站的访问',
    '',
    'User-agent: *',
    '# 允许爬取所有公共页面',
    'Allow: /',
    '',
    '# 禁止爬取：管理后台、需要登录的用户端、以及判为不值得收录的公共页'
  ]
  for (const rule of disallowRules()) lines.push(`Disallow: ${rule}`)
  lines.push(
    '',
    `Crawl-delay: 1`,
    '',
    `Sitemap: ${SITE_ORIGIN}/sitemap.xml`,
    '',
    `Host: ${SITE_ORIGIN.replace(/^https?:\/\//, '')}`,
    ''
  )
  return lines.join('\n')
}

/** sitemap.xml 的正文 */
export function sitemapXml() {
  const blocks = sitemapPages().map((p) => [
    '  <url>',
    `    <loc>${SITE_ORIGIN}${p.path}</loc>`,
    `    <changefreq>${p.changefreq}</changefreq>`,
    `    <priority>${p.priority}</priority>`,
    '  </url>'
  ].join('\n'))
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    `<!-- ${GENERATED_MARK} —— 内容来自 seo/site.js，不要手改本文件 -->`,
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
    '        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
    '        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9',
    '        http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">',
    '',
    ...blocks,
    '',
    '</urlset>',
    ''
  ].join('\n')
}
