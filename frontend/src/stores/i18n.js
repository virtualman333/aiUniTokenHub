import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import zhCN from '@/locales/zh-CN'
import enUS from '@/locales/en-US'

const messages = {
  'zh-CN': zhCN,
  'en-US': enUS
}

export const useI18nStore = defineStore('i18n', () => {
  const locale = ref(localStorage.getItem('locale') || 'zh-CN')

  const t = (key) => {
    const keys = key.split('.')
    let value = messages[locale.value]
    for (const k of keys) {
      if (value && value[k]) {
        value = value[k]
      } else {
        return key
      }
    }
    return value
  }

  const setLocale = (newLocale) => {
    locale.value = newLocale
  }

  watch(locale, (newLocale) => {
    localStorage.setItem('locale', newLocale)
    document.documentElement.setAttribute('lang', newLocale)
  }, { immediate: true })

  return {
    locale,
    t,
    setLocale
  }
})
