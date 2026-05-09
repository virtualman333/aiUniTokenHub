<template>
  <div v-if="false" aria-hidden="true">
    <!-- 此组件仅用于设置 SEO Meta 信息，不渲染任何内容 -->
  </div>
</template>

<script setup>
import { useSeoMeta } from '@/composables/useSeoMeta'

const props = defineProps({
  title: {
    type: String,
    default: ''
  },
  description: {
    type: String,
    default: ''
  },
  keywords: {
    type: String,
    default: ''
  },
  ogImage: {
    type: String,
    default: ''
  },
  noIndex: {
    type: Boolean,
    default: false
  }
})

// 使用 composable 设置 SEO Meta 信息
useSeoMeta({
  title: props.title,
  description: props.description,
  keywords: props.keywords,
  ogImage: props.ogImage,
  noIndex: props.noIndex
})
</script>
