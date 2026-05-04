<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">控制台</h2>
    </div>
    
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-value">{{ overview.total_requests || 0 }}</div>
          <div class="stat-label">总请求数</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #67C23A, #85ce61);">
          <div class="stat-value">{{ overview.today_requests || 0 }}</div>
          <div class="stat-label">今日请求</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #E6A23C, #ebb563);">
          <div class="stat-value">{{ overview.success_rate || 100 }}%</div>
          <div class="stat-label">成功率</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #909399, #a6a9ad);">
          <div class="stat-value">{{ overview.avg_response_time || 0 }}ms</div>
          <div class="stat-label">平均响应时间</div>
        </div>
      </el-col>
    </el-row>
    
    <!-- 图表区域 -->
    <el-row :gutter="20">
      <el-col :span="16">
        <div class="card">
          <div class="card-title">请求趋势</div>
          <div ref="requestChartRef" style="height: 300px;"></div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card">
          <div class="card-title">热门API</div>
          <el-table :data="topAPIs" size="small">
            <el-table-column prop="name" label="API名称" />
            <el-table-column prop="count" label="调用次数" width="100" align="right" />
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useDashboardStore } from '@/stores'
import * as echarts from 'echarts'

const dashboardStore = useDashboardStore()

const overview = ref({})
const topAPIs = ref([])
const requestStats = ref([])
const requestChartRef = ref(null)
let requestChart = null

onMounted(async () => {
  await loadData()
  initChart()
})

onUnmounted(() => {
  requestChart?.dispose()
})

const loadData = async () => {
  try {
    overview.value = await dashboardStore.fetchOverview()
    topAPIs.value = await dashboardStore.fetchTopAPIs(5)
    requestStats.value = await dashboardStore.fetchRequestStats(7)
    updateChart()
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

const initChart = () => {
  if (!requestChartRef.value) return
  requestChart = echarts.init(requestChartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!requestChart) return
  
  const dates = requestStats.value.map(s => s.date)
  const counts = requestStats.value.map(s => s.count)
  
  requestChart.setOption({
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

<style lang="scss" scoped>
.stat-row {
  margin-bottom: 20px;
}

.card {
  .card-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 16px;
    color: #333;
  }
}
</style>
