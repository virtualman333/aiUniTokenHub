import { useI18nStore } from '@/stores/i18n'

export function useI18n() {
  const i18nStore = useI18nStore()
  
  return {
    locale: i18nStore.locale,
    t: i18nStore.t,
    setLocale: i18nStore.setLocale
  }
}
