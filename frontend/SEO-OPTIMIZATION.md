# SEO 优化文档

## 已完成的 SEO 优化

### 1. 基础 Meta 标签优化 (`index.html`)

已添加以下 Meta 标签：

- **基础标签**: description, keywords, author, robots, theme-color, application-name
- **Open Graph 标签**: og:type, og:title, og:description, og:url, og:site_name, og:locale, og:image
- **Twitter Card 标签**: twitter:card, twitter:title, twitter:description, twitter:image
- **其他优化**: canonical URL, DNS 预解析, preconnect

### 2. 动态 Meta 标签管理

安装了 `@vueuse/head` 并在路由守卫中动态更新 Meta 标签：

- 每个路由都可以设置独立的 title, description, keywords
- 管理后台页面自动设置 `noindex, nofollow`
- 支持自定义 OG 图片和 URL

### 3. 路由 Meta 信息

已为以下路由添加 SEO Meta 信息：

**公共页面：**
- `/` - 首页
- `/login` - 登录
- `/register` - 注册
- `/forgot-password` - 忘记密码
- `/privacy-policy` - 隐私政策
- `/terms-of-service` - 用户协议

**用户端页面（需要登录）：**
- `/app` - 控制台
- `/app/api-doc` - 接口文档
- `/app/model-square` - 模型广场
- `/app/chat` - AI 对话
- `/app/my-keys` - 我的密钥
- `/app/usage-log` - 使用记录
- `/app/settings` - 账户设置
- `/app/billing` - 账单中心
- `/app/tickets` - 工单中心
- `/app/tutorial` - 接入教程

**管理端页面（noIndex）：**
- 所有 `/admin/*` 路由都设置了 `noindex, nofollow`

### 4. 结构化数据 (JSON-LD)

在 `index.html` 中添加了三种结构化数据：

1. **WebSite** - 网站信息，包含搜索动作
2. **Organization** - 组织信息
3. **SoftwareApplication** - 软件应用信息

### 5. robots.txt

已创建 `public/robots.txt`，配置如下：

- 允许爬取所有公共页面
- 禁止爬取管理后台和需要登录的页面
- 指向 sitemap.xml 位置

### 6. sitemap.xml

已创建 `public/sitemap.xml`，包含以下公共页面：

- `https://unitokenhub.m3it.cn/`
- `https://unitokenhub.m3it.cn/login`
- `https://unitokenhub.m3it.cn/register`
- `https://unitokenhub.m3it.cn/forgot-password`
- `https://unitokenhub.m3it.cn/privacy-policy`
- `https://unitokenhub.m3it.cn/terms-of-service`

### 7. 可复用组件

创建了 `src/components/SeoMeta.vue` 组件，可在页面中使用：

```vue
<SeoMeta
  title="页面标题"
  description="页面描述"
  keywords="关键词1,关键词2"
  :noIndex="false"
/>
```

### 8. Composable

创建了 `src/composables/useSeoMeta.js`，可在 setup 中使用：

```javascript
import { useSeoMeta } from '@/composables/useSeoMeta'

useSeoMeta({
  title: '页面标题',
  description: '页面描述',
  keywords: '关键词1,关键词2',
  noIndex: false
})
```

## 待完成任务

### 1. 创建 OG 图片

需要在 `public/assets/images/og-image.png` 创建一个 1200x630 像素的图片，用于社交分享。

**要求：**
- 尺寸：1200x630 像素（Open Graph 推荐尺寸）
- 格式：PNG 或 JPG
- 内容：包含 uniTokenHub Logo 和标语
- 背景：与网站主题色一致（#409EFF 或渐变）

### 2. 启用预渲染（可选）

已安装 `vite-plugin-prerender`，但暂时禁用。要启用：

1. 运行以下命令批准构建脚本：
   ```bash
   pnpm approve-builds @parcel/watcher esbuild puppeteer vue-demi
   ```

2. 在 `vite.config.js` 中取消预渲染插件的注释

3. 重新构建项目

**注意：** 预渲染可以为公共页面生成静态 HTML，有利于 SEO，但需要正确配置 Puppeteer。

### 3. 提交到搜索引擎

完成 OG 图片创建后，提交 sitemap 到：

- [Google Search Console](https://search.google.com/search-console)
- [Bing Webmaster Tools](https://www.bing.com/webmasters)
- [百度站长平台](https://ziyuan.baidu.com/)

### 4. 监控和分析

建议集成以下工具来监控 SEO 效果：

- Google Analytics（已有或建议添加）
- Google Search Console
- 百度统计（针对中文用户）

## 使用方法

### 在页面组件中使用 SeoMeta 组件：

```vue
<template>
  <div>
    <SeoMeta
      title="我的页面"
      description="这是我的页面描述"
      keywords="关键词1,关键词2,关键词3"
    />
    <!-- 页面内容 -->
  </div>
</template>

<script setup>
import SeoMeta from '@/components/SeoMeta.vue'
</script>
```

### 在 setup 中使用 useSeoMeta composable：

```vue
<script setup>
import { useSeoMeta } from '@/composables/useSeoMeta'

useSeoMeta({
  title: '我的页面',
  description: '这是我的页面描述',
  keywords: '关键词1,关键词2',
  noIndex: false
})
</script>
```

### 在路由中配置 Meta 信息（已实现）：

路由配置中的 `meta` 字段已包含 SEO 信息，路由守卫会自动应用这些设置。

## 技术栈

- **@vueuse/head**: ^2.0.0 - 动态管理文档头部
- **vite-plugin-prerender**: ^1.0.8 - 预渲染静态 HTML（可选）

## 构建和部署

```bash
# 安装依赖
pnpm install

# 开发模式
pnpm dev

# 生产构建
pnpm build

# 预览构建结果
pnpm preview
```

## 注意事项

1. **OG 图片必须创建**：`index.html` 中引用了 `https://unitokenhub.m3it.cn/assets/images/og-image.png`，需要创建此文件。

2. **规范 URL**：所有规范 URL 都指向 `https://unitokenhub.m3it.cn/`，部署时请确认为正确域名。

3. **预渲染**：当前禁用预渲染，如需启用请参考上述"待完成任务"部分。

4. **搜索引擎索引**：管理后台页面已设置 `noindex`，不会被搜索引擎索引。

## 检查清单

- [x] 基础 Meta 标签（description, keywords, author）
- [x] Open Graph 标签
- [x] Twitter Card 标签
- [x] 结构化数据 (JSON-LD)
- [x] robots.txt
- [x] sitemap.xml
- [x] 动态 Meta 标签管理
- [x] 路由 Meta 信息
- [x] 可复用 SeoMeta 组件
- [x] useSeoMeta composable
- [ ] OG 图片（需要创建）
- [ ] 启用预渲染（可选）
- [ ] 提交 sitemap 到搜索引擎
- [ ] 集成分析工具

## 参考资料

- [Google SEO 指南](https://developers.google.com/search/docs/beginner/seo-starter-guide)
- [Open Graph 协议](https://ogp.me/)
- [Twitter Card 文档](https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/abouts-cards)
- [Schema.org 结构化数据](https://schema.org/)
- [Vite 预渲染插件](https://github.com/vitejs/vite-plugin-prerender)
