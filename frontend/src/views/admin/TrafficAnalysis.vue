<template>
  <div class="traffic-analysis">
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)">
          <el-icon><DataLine /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.totalRequests }}</div>
          <div class="stat-title">总请求数</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%)">
          <el-icon><Check /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.successRate }}%</div>
          <div class="stat-title">成功率</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)">
          <el-icon><Timer /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.avgResponseTime }}ms</div>
          <div class="stat-title">平均响应时间</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)">
          <el-icon><User /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.activeUsers }}</div>
          <div class="stat-title">活跃用户</div>
        </div>
      </div>
    </div>

    <!-- 时间范围选择 -->
    <div class="time-range-bar">
      <el-radio-group v-model="timeRange" @change="loadData">
        <el-radio-button label="today">今天</el-radio-button>
        <el-radio-button label="yesterday">昨天</el-radio-button>
        <el-radio-button label="7days">近7天</el-radio-button>
        <el-radio-button label="30days">近30天</el-radio-button>
        <el-radio-button label="custom">自定义</el-radio-button>
      </el-radio-group>
      
      <el-date-picker
        v-if="timeRange === 'custom'"
        v-model="customDateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="loadData"
        style="margin-left: 16px"
      />
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <el-card class="chart-card">
        <template #header>
          <div class="card-header">
            <span>请求趋势</span>
          </div>
        </template>
        <div class="chart-container" ref="trendChartRef"></div>
      </el-card>

      <el-card class="chart-card">
        <template #header>
          <span>状态码分布</span>
        </template>
        <div class="chart-container" ref="statusChartRef"></div>
      </el-card>
    </div>

    <div class="charts-row">
      <el-card class="chart-card">
        <template #header>
          <span>模型调用分布</span>
        </template>
        <div class="chart-container" ref="modelChartRef"></div>
      </el-card>

      <el-card class="chart-card">
        <template #header>
          <span>响应时间分布</span>
        </template>
        <div class="chart-container" ref="responseTimeChartRef"></div>
      </el-card>
    </div>

    <!-- 表格区域 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>热门模型 TOP10</span>
          </template>
          <el-table :data="topModels" stripe size="small">
            <el-table-column prop="model_name" label="模型名称" min-width="150" />
            <el-table-column prop="request_count" label="请求数" width="100" align="center" />
            <el-table-column prop="avg_response_time" label="平均响应时间" width="120" align="center">
              <template #default="{ row }">
                {{ row.avg_response_time }}ms
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>活跃用户 TOP10</span>
          </template>
          <el-table :data="topUsers" stripe size="small">
            <el-table-column prop="username" label="用户名" min-width="120" />
            <el-table-column prop="request_count" label="请求数" width="100" align="center" />
            <el-table-column prop="total_tokens" label="总Token消耗" width="120" align="center">
              <template #default="{ row }">
                {{ formatNumber(row.total_tokens) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, markRaw } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import api from '@/stores'
import { 
  DataLine, Check, Timer, User 
} from '@element-plus/icons-vue'

// 统计数据
const stats = ref({
  totalRequests: 0,
  successRate: 0,
  avgResponseTime: 0,
  activeUsers: 0
})

// 时间范围
const timeRange = ref('today')
const customDateRange = ref([])

// 图表引用
const trendChartRef = ref(null)
const statusChartRef = ref(null)
const modelChartRef = ref(null)
const responseTimeChartRef = ref(null)

// 图表实例
let trendChart = null
let statusChart = null
let modelChart = null
let responseTimeChart = null

// 表格数据
const topModels = ref([])
const topUsers = ref([])

// 加载数据
async function loadData() {
  try {
    const params = buildQueryParams()
    
    // 获取统计数据
    const statsRes = await api.get('/api/traffic/stats/', { params })
    stats.value = statsRes
    
    // 获取趋势数据
    const trendRes = await api.get('/api/traffic/trend/', { params })
    renderTrendChart(trendRes)
    
    // 获取状态码分布
    const statusRes = await api.get('/api/traffic/status-distribution/', { params })
    renderStatusChart(statusRes)
    
    // 获取模型分布
    const modelRes = await api.get('/api/traffic/model-distribution/', { params })
    renderModelChart(modelRes)
    
    // 获取响应时间分布
    const responseTimeRes = await api.get('/api/traffic/response-time-distribution/', { params })
    renderResponseTimeChart(responseTimeRes)
    
    // 获取TOP数据
    const topRes = await api.get('/api/traffic/top/', { params })
    topModels.value = topRes.models || []
    topUsers.value = topRes.users || []
  } catch (error) {
    ElMessage.error('加载数据失败')
    console.error(error)
  }
}

// 构建查询参数
function buildQueryParams() {
  const params = {}
  
  if (timeRange.value === 'custom' && customDateRange.value.length === 2) {
    params.start_date = customDateRange.value[0].toISOString().split('T')[0]
    params.end_date = customDateRange.value[1].toISOString().split('T')[0]
  } else {
    params.time_range = timeRange.value
  }
  
  return params
}

// 渲染趋势图
function renderTrendChart(data) {
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
  
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['总请求', '成功请求', '失败请求'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: data.labels || [] },
    yAxis: { type: 'value' },
    series: [
      { name: '总请求', type: 'line', data: data.total || [], smooth: true },
      { name: '成功请求', type: 'line', data: data.success || [], smooth: true },
      { name: '失败请求', type: 'line', data: data.failed || [], smooth: true }
    ]
  }
  
  trendChart.setOption(option)
}

// 渲染状态码分布图
function renderStatusChart(data) {
  if (!statusChart) {
    statusChart = echarts.init(statusChartRef.value)
  }
  
  const option = {
    tooltip: { trigger: 'item', formatter: '{a} <br/>{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      name: '状态码',
      type: 'pie',
      radius: '50%',
      data: data || [],
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }
      }
    }]
  }
  
  statusChart.setOption(option)
}

// 渲染模型分布图
function renderModelChart(data) {
  if (!modelChart) {
    modelChart = echarts.init(modelChartRef.value)
  }
  
  const option = {
    tooltip: { trigger: 'item', formatter: '{a} <br/>{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      name: '模型调用',
      type: 'pie',
      radius: ['40%', '70%'],
      data: data || [],
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }
      }
    }]
  }
  
  modelChart.setOption(option)
}

// 渲染响应时间分布图
function renderResponseTimeChart(data) {
  if (!responseTimeChart) {
    responseTimeChart = echarts.init(responseTimeChartRef.value)
  }
  
  const option = {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: data.labels || [] },
    yAxis: { type: 'value' },
    series: [{
      name: '响应时间',
      type: 'bar',
      data: data.data || []
    }]
  }
  
  responseTimeChart.setOption(option)
}

// 格式化数字
function formatNumber(num) {
  if (!num) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w'
  }
  return num.toString()
}

// 监听窗口大小变化
function handleResize() {
  trendChart?.resize()
  statusChart?.resize()
  modelChart?.resize()
  responseTimeChart?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  statusChart?.dispose()
  modelChart?.dispose()
  responseTimeChart?.dispose()
})
</script>

<style scoped>
.traffic-analysis {
  padding: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.2;
}

.stat-title {
  font-size: 14px;
  color: #6b7280;
  margin-top: 4px;
}

.time-range-bar {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.chart-card {
  border-radius: 12px;
}

.chart-container {
  height: 300px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

@media (max-width: 1024px) {
  .charts-row {
    grid-template-columns: 1fr;
  }
}
</style>
