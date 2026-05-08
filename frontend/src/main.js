import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import en from 'element-plus/dist/locale/en.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import router from './router'
import App from './App.vue'
import faviconUrl from '@/assets/image/logo_48x48.ico'
import './styles/index.scss'
import './styles/theme.scss'
import { useI18nStore } from './stores/i18n'

// 动态设置浏览器标签页的 favicon
function setFavicon(href) {
  let link = document.querySelector("link[rel~='icon']")
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  link.type = 'image/x-icon'
  link.href = href
}
setFavicon(faviconUrl)

const pinia = createPinia()
const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)

// 使用 pinia 后才能初始化 i18n
const i18nStore = useI18nStore()
const elementLocale = i18nStore.locale === 'zh-CN' ? zhCn : en
app.use(ElementPlus, { locale: elementLocale })

app.mount('#app')
