<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  data: Array<{ date: string; count: number }>
}>()

const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  chart?.dispose()
})

watch(() => props.data, updateChart, { deep: true })

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  updateChart()
}

function updateChart() {
  if (!chart) return
  
  const dates = props.data.map(s => s.date)
  const counts = props.data.map(s => s.count)
  
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false
    },
    yAxis: { type: 'value' },
    series: [{
      name: '请求数',
      type: 'line',
      data: counts,
      smooth: true,
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.5)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
        ])
      },
      itemStyle: { color: '#409EFF' },
    }]
  })
}
</script>

<style scoped>
.chart-container {
  height: 300px;
  width: 100%;
}
</style>
