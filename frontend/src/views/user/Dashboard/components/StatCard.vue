<template>
  <div class="stat-card" :style="cardStyle">
    <div class="stat-icon">
      <el-icon :size="24"><component :is="icon" /></el-icon>
    </div>
    <div class="stat-content">
      <div class="stat-value">{{ value }}</div>
      <div class="stat-label">{{ label }}</div>
    </div>
    <div class="stat-trend" v-if="trend">
      <el-icon :size="14"><component :is="trendIcon" /></el-icon>
      <span>{{ trend }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { TrendCharts, TrendCharts as TrendChartsIcon } from '@element-plus/icons-vue'

const props = defineProps<{
  value: string | number
  label: string
  gradient?: string
  icon?: any
  trend?: string
  trendUp?: boolean
}>()

const cardStyle = computed(() => ({
  background: props.gradient || 'var(--gradient-primary)'
}))

const trendIcon = computed(() => props.trendUp ? 'ArrowUp' : 'ArrowDown')
</script>

<style scoped>
.stat-card {
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  color: var(--text-inverse);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  position: relative;
  overflow: hidden;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0) 100%);
    pointer-events: none;
  }
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
  }
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  margin-bottom: var(--space-1);
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.stat-label {
  font-size: var(--text-sm);
  opacity: 0.9;
  font-weight: var(--font-medium);
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  background: rgba(255, 255, 255, 0.2);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-full);
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
}

@media (max-width: 768px) {
  .stat-card {
    padding: var(--space-4);
    flex-direction: column;
    text-align: center;
    gap: var(--space-3);
  }
  
  .stat-icon {
    width: 48px;
    height: 48px;
  }
  
  .stat-value {
    font-size: var(--text-2xl);
  }
  
  .stat-trend {
    position: static;
    margin-top: var(--space-2);
  }
}
</style>
