<template>
  <div class="stat-card" :style="gradientStyle">
    <div class="stat-value">{{ value }}</div>
    <div class="stat-label">{{ label }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  value: string | number
  label: string
  gradient?: string
}>()

const gradientStyle = {
  background: 'linear-gradient(135deg, #409EFF, #66b1ff)'
}
</script>

<style scoped>
.stat-card {
  padding: 24px;
  border-radius: 12px;
  color: white;
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
}
</style>
