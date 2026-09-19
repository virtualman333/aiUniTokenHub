# SEO 优化文档

> **先说唯一来源在哪：** 「哪些页面要被搜索引擎收录」只由 `seo/site.js` 里的
> `PUBLIC_PAGES[].indexable` 与 `PRIVATE_PREFIXES` 决定。
> `public/robots.txt` 与 `public/sitemap.xml` **是生成物**，改它们没用 —— 改完跑一次
> `node scripts/check-seo.js` 就会红，因为产物必须与唯一来源逐字节一致。

## 一、实际在生效的机制

SEO 这件事在本仓库由**一条路径**负责，别的地方都不要插一手：

| 关注点 | 实现位置 | 怎么被守住 |
| --- | --- | --- |
| 每个页面的 title / description / keywords / robots / OG / canonical | `src/router/index.js` 的 `router.afterEach`（按 `meta` 现写 DOM） | `router` 的 `meta` 是唯一入口；`scripts/check-seo.js` 检查 `/admin` 下每条路由的 `noIndex` |
| 收录范围（谁能被爬、提交哪些 URL） | `seo/site.js` | `scripts/check-seo.js` 拿 sitemap ⇄ robots ⇄ 路由表三向对账 |
| 静态初值（爬虫不执行 JS 时看到的那一份） | `index.html` 的 meta + JSON-LD | 检查 JSON-LD 里每个本站 URL 都对应真实路由；检查 robots 初值不是 `noindex` |
| 产物落盘 | `scripts/gen-seo.js` | 产物带 `GENERATED-BY scripts/gen-seo.js` 标记，手改即被 `check-seo.js` 发现 |

### 为什么不用 `@vueuse/head`

`@vueuse/head` 仍然装着（`src/main.js` 里 `createHead()` + `app.use(head)`），
但**当前没有任何页面用它**：它与 `router.afterEach` 会抢同一批标签，而它的 `noIndex`
默认值是 `false` —— 在后台页上用一次，就会把已经写好的 `noindex, nofollow` 覆盖回
`index, follow`。

此前仓库里有一条走这条路、却**全仓零调用**的实现（一个 `SeoMeta` 组件 + 一个
`useSeoMeta` composable），本文档还把它写成了「已完成」并附上了「使用方法」。
两者已一并删除：`scripts/check-seo.js` 会拦住 `useHead(` 复活，也拦住那两条路径
在文档里重新出现。真要用它，先把调用点接上真页面，再删掉那条检查。

## 二、`seo/site.js` 里的产品决定

`indexable` 决定一切，改一列就等于改了收录范围：

| 路径 | indexable | 说明 |
| --- | --- | --- |
| `/` | 是 | 首页 |
| `/login` | 是 | 品牌词检索的落地页。旧 `robots.txt` 挡住了它，而旧 `sitemap.xml` 又按 `priority 0.8` 提交它 —— 两边打架，被提交的 URL 永远进不了索引 |
| `/register` | 是 | 转化页，同上 |
| `/forgot-password` | **否** | 没有检索价值，只会引来「重置密码」类垃圾流量。旧 sitemap 按 `0.3` 提交了它，与 robots 的 Disallow 直接矛盾 |
| `/privacy-policy` | 是 | |
| `/terms-of-service` | 是 | |

`PRIVATE_PREFIXES` 里的 `/admin/` 与 `/app/` 一律不收录：用户端所有页面在 router 里都
继承 `requiresAuth: true`，爬虫拿到的只是一个跳转。**想让 `/app/api-doc`、`/app/model-square`
这些有 SEO 价值的页面被收录，要先把它们改成不要求登录，而不是改 robots.txt。**

`<lastmod>` 刻意不放：旧的六条 URL 全是同一个 `2026-05-09`，四个月没人维护过，
而 Google 对 `lastmod` 的口径是「一致且可验证才用」—— 一个明显失真的日期只会被忽略，
还会拖累整份 sitemap 的可信度。没有 `lastmod` 比一个假的 `lastmod` 好。

## 三、改收录范围 / 改 SEO 的操作

```bash
cd frontend

# 1. 改 seo/site.js（PUBLIC_PAGES / PRIVATE_PREFIXES）
# 2. 重新生成两份产物
pnpm run gen:seo

# 3. 核对（产物、sitemap ⇄ robots ⇄ 路由表、JSON-LD、后台 noIndex）
pnpm run check:seo

# 4. 起本地预览
pnpm run preview
```

`pnpm run check:seo` 已经串在 `npm run build` 的最前面 —— 产物和唯一来源不一致时
**构建会直接失败**，不会把错版 sitemap 发上线。

要只看不写，`node scripts/gen-seo.js --check` 只比对、不落盘。

（本仓入库的锁文件是 `pnpm-lock.yaml`，所以前端命令默认按 pnpm 写。）

## 四、还没做的（明确记着，别当成已做）

### 1. OG 图片

`index.html` 与 `seo/site.js` 里引用的 `https://unitokenhub.m3it.cn/assets/images/og-image.png`
**不在前端产物里** —— `/assets/` 由反向代理直接服务（favicon 也走那里），所以本仓库里
查不到它是正常现象，检查也只核对域名。

要确认它到底在不在，得在部署机上直接请求那个地址。需要的规格：

- 尺寸 1200×630，PNG 或 JPG
- 内容：uniTokenHub 标识 + 一句话
- 背景：主题色 `#409EFF` 或同色系渐变

### 2. 预渲染（可选）

`vite-plugin-prerender` 已安装但**未启用**。启用步骤：

```bash
pnpm approve-builds @parcel/watcher esbuild puppeteer vue-demi
```

然后在 `vite.config.js` 中取消预渲染插件的注释，重新构建。

为什么没启用：预渲染要为公共页生成静态 HTML，需要 Puppeteer 正确配置；
而当前站点公共页只有 6 个，收益与运维成本要先算清楚再决定。
**不启用不影响 sitemap / robots / meta 的正确性** —— 上面那套检查与它无关。

### 3. 提交与监控

sitemap 提交到 [Google Search Console](https://search.google.com/search-console)、
[Bing Webmaster Tools](https://www.bing.com/webmasters)、
[百度站长平台](https://ziyuan.baidu.com/)。

> 提交后如果 Search Console 报「Blocked by robots.txt」，现在这版不会再出现 ——
> 那正是本轮修掉的缺陷（提交了被自己家 robots.txt 挡住的 URL）。

## 五、技术栈

- **vue-router**：`afterEach` 钩子按路由 `meta` 现写 meta 标签（本仓唯一在跑的机制）
- **@vueuse/head**：^2.0.0，仍安装，当前无调用点（见第一节）
- **vite-plugin-prerender**：^1.0.8，未启用（见第四节）
