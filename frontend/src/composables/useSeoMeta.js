import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useHead } from '@vueuse/head'

/**
 * SEO Meta 管理 Composable
 * 用于在页面组件中动态设置 SEO 相关的 meta 标签
 */
export function useSeoMeta(options = {}) {
  const route = useRoute()
  
  const defaults = {
    title: 'uniTokenHub - 统一API中转服务',
    titleTemplate: '%s | uniTokenHub',
    description: 'uniTokenHub - 开箱即用的统一API中转服务与网关框架，支持AI API聚合、OpenAI兼容接口、多模型管理、密钥管理与计费系统。',
    keywords: 'API中转,API网关,AI API,OpenAI API,Claude API,API聚合,API管理平台',
    ogImage: 'https://unitokenhub.m3it.cn/assets/images/og-image.png',
    ogUrl: 'https://unitokenhub.m3it.cn/',
    noIndex: false,
  }
  
  const meta = { ...defaults, ...options }
  
  // 构建完整的 URL
  const fullUrl = computed(() => {
    return meta.ogUrl.replace(/\/$/, '') + route.fullPath
  })
  
  // 构建完整的标题
  const fullTitle = computed(() => {
    if (meta.title === defaults.title) {
      return meta.title
    }
    return meta.titleTemplate.replace('%s', meta.title)
  })
  
  useHead({
    title: fullTitle,
    meta: [
      // 基础 Meta
      { name: 'description', content: meta.description },
      { name: 'keywords', content: meta.keywords },
      { name: 'robots', content: meta.noIndex ? 'noindex, nofollow' : 'index, follow' },
      
      // Open Graph
      { property: 'og:title', content: meta.title },
      { property: 'og:description', content: meta.description },
      { property: 'og:type', content: 'website' },
      { property: 'og:url', content: fullUrl },
      { property: 'og:image', content: meta.ogImage },
      { property: 'og:site_name', content: 'uniTokenHub' },
      { property: 'og:locale', content: 'zh_CN' },
      
      // Twitter Card
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: meta.title },
      { name: 'twitter:description', content: meta.description },
      { name: 'twitter:image', content: meta.ogImage },
    ],
    link: [
      { rel: 'canonical', href: fullUrl },
    ],
  })
  
  return {
    fullTitle,
    fullUrl,
  }
}
