<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">管理后台</h2>
    </div>
    
    <!-- 统计概览 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-value">{{ stats.users?.total || 0 }}</div>
          <div class="stat-label">用户总数</div>
          <div class="stat-extra">今日新增: {{ stats.users?.new_today || 0 }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #67C23A, #85ce61);">
          <div class="stat-value">{{ stats.api_keys?.total || 0 }}</div>
          <div class="stat-label">API密钥</div>
          <div class="stat-extra">活跃: {{ stats.api_keys?.active || 0 }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #E6A23C, #ebb563);">
          <div class="stat-value">{{ stats.apis?.total || 0 }}</div>
          <div class="stat-label">API总数</div>
          <div class="stat-extra">分类: {{ stats.apis?.categories || 0 }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #909399, #a6a9ad);">
          <div class="stat-value">{{ overview.total_requests || 0 }}</div>
          <div class="stat-label">总请求数</div>
          <div class="stat-extra">今日: {{ overview.today_requests || 0 }}</div>
        </div>
      </el-col>
    </el-row>
    
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card header="请求趋势">
          <div ref="chartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card header="热门API">
          <el-table :data="topAPIs" size="small">
            <el-table-column prop="name" label="API名称" />
            <el-table-column prop="count" label="调用次数" width="100" align="right" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useDashboardStore } from '@/stores'
import api from '@/stores'
import * as echarts from 'echarts'

const dashboardStore = useDashboardStore()
const stats = ref({})
const overview = ref({})
const topAPIs = ref([])
const requestStats = ref([])
const chartRef = ref(null)
let chart = null

onMounted(async () => {
  await loadData()
  initChart()
})

onUnmounted(() => {
  chart?.dispose()
})

const loadData = async () => {
  try {
    const [adminStats, overviewData, topData, statsData] = await Promise.all([
      api.get('/dashboard/admin_stats/'),
      dashboardStore.fetchOverview(),
      dashboardStore.fetchTopAPIs(10),
      dashboardStore.fetchRequestStats(7)
    ])
    stats.value = adminStats
    overview.value = overviewData
    topAPIs.value = topData
    requestStats.value = statsData
    updateChart()
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

const initChart = () => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
}

const updateChart = () => {
  if (!chart) return
  
  const dates = requestStats.value.map(s => s.date)
  const counts = requestStats.value.map(s => s.count)
  
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: { type: 'value' },
    series: [{
      name: '请求数',
      type: 'line',
      data: counts,
      smooth: true,
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(64, 158, 255, 0.5)' },
        { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
      ])},
      itemStyle: { color: '#409EFF' }
    }]
  })
}
</script>

<style lang="scss" scoped>
.stat-row {
  margin-bottom: 20px;
}

.stat-card {
  .stat-extra {
    font-size: 12px;
    margin-top: 8px;
    opacity: 0.8;
  }
}
</style>
