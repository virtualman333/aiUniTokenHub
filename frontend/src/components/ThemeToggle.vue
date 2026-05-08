<template>
  <el-tooltip :content="i18n.t(theme === 'light' ? 'common.switchToDark' : 'common.switchToLight')">
    <el-button :icon="theme === 'light' ? Moon : Sunny" circle @click="toggleTheme" />
  </el-tooltip>
</template>

<script setup>
import { useThemeStore } from '@/stores/theme'
import { useI18nStore } from '@/stores/i18n'
import { Moon, Sunny } from '@element-plus/icons-vue'

const themeStore = useThemeStore()
const i18n = useI18nStore()
const theme = themeStore.theme
const toggleTheme = themeStore.toggleTheme
</script>
