<template>
  <el-dropdown @command="handleCommand">
    <el-button circle>
      <el-icon>
        <GlobeIcon />
      </el-icon>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="zh-CN" :class="{ 'is-active': locale === 'zh-CN' }">
          中文
        </el-dropdown-item>
        <el-dropdown-item command="en-US" :class="{ 'is-active': locale === 'en-US' }">
          English
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import { useI18nStore } from '@/stores/i18n'

const i18nStore = useI18nStore()
const locale = i18nStore.locale
const handleCommand = (cmd) => {
  i18nStore.setLocale(cmd)
}
</script>

<script>
// 自定义 Globe SVG 图标组件
import { h } from 'vue'

export const GlobeIcon = {
  render() {
    return h('svg', {
      viewBox: '0 0 24 24',
      fill: 'none',
      xmlns: 'http://www.w3.org/2000/svg',
      width: '1em',
      height: '1em'
    }, [
      h('circle', {
        cx: '12',
        cy: '12',
        r: '10',
        stroke: 'currentColor',
        strokeWidth: '2',
        strokeLinecap: 'round',
        strokeLinejoin: 'round'
      }),
      h('path', {
        d: 'M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20',
        stroke: 'currentColor',
        strokeWidth: '2',
        strokeLinecap: 'round'
      }),
      h('path', {
        d: 'M12 2a14.5 14.5 0 0 1 0 20 14.5 14.5 0 0 1 0-20',
        stroke: 'currentColor',
        strokeWidth: '2',
        strokeLinecap: 'round'
      }),
      h('path', {
        d: 'M2 12h20',
        stroke: 'currentColor',
        strokeWidth: '2',
        strokeLinecap: 'round'
      }),
      h('path', {
        d: 'M12 2c-1.5 2-3 4.5-3 8 0 3.5 1.5 6 3 8',
        stroke: 'currentColor',
        strokeWidth: '2',
        strokeLinecap: 'round'
      }),
      h('path', {
        d: 'M12 2c1.5 2 3 4.5 3 8 0 3.5-1.5 6-3 8',
        stroke: 'currentColor',
        strokeWidth: '2',
        strokeLinecap: 'round'
      })
    ])
  }
}
</script>

<style scoped>
.is-active {
  color: var(--el-color-primary);
  font-weight: 600;
}
</style>
