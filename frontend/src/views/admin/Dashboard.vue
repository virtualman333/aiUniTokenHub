<template>
  <div class="admin-dashboard">
    <!-- 快捷操作栏 -->
    <div class="quick-actions">
      <el-button type="primary" @click="$router.push('/admin/recharge-management')">
        <el-icon><Wallet /></el-icon>
        充值管理
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" v-for="stat in stats" :key="stat.title">
        <div class="stat-icon" :style="{ background: stat.bgColor }">
          <el-icon><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-title">{{ stat.title }}</div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <el-card class="chart-card">
        <template #header>
          <div class="card-header">
            <span>请求趋势</span>
            <el-radio-group v-model="chartDays" size="small">
              <el-radio-button label="7">近7天</el-radio-button>
              <el-radio-button label="30">近30天</el-radio-button>
            </el-radio-group>
          </div>
        </template>
        <div class="chart-container" ref="trendChartRef"></div>
      </el-card>

      <el-card class="chart-card">
        <template #header>
          <span>API调用分布</span>
        </template>
        <div class="chart-container" ref="pieChartRef"></div>
      </el-card>
    </div>

    <!-- 错误率趋势 -->
    <div class="charts-row" style="margin-top: 20px;">
      <el-card class="chart-card">
        <template #header>
          <div class="card-header">
            <span>错误率趋势（近7天）</span>
          </div>
        </template>
        <div class="chart-container" ref="errorChartRef"></div>
      </el-card>

      <el-card class="chart-card">
        <template #header>
          <span>Token消耗排行（本月）</span>
        </template>
        <el-table :data="tokenStats.model_stats || []" stripe size="small">
          <el-table-column prop="model_name" label="模型名称" min-width="120" />
          <el-table-column prop="request_count" label="请求数" width="100" align="center" />
          <el-table-column prop="total_tokens" label="Token消耗" width="120" align="center">
            <template #default="{ row }">
              {{ formatNumber(row.total_tokens) }}
            </template>
          </el-table-column>
          <el-table-column prop="total_cost" label="成本" width="100" align="center">
            <template #default="{ row }">
              ¥{{ Number(row.total_cost || 0).toFixed(4) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 活跃用户排行 -->
    <el-card class="table-card" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>活跃用户排行（近7天）</span>
          <el-button type="primary" link @click="$router.push('/admin/users')">
            查看全部
          </el-button>
        </div>
      </template>
      <el-table :data="activeUsers.top_users || []" stripe>
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="request_count" label="请求数" width="120" align="center" sortable />
        <el-table-column prop="total_tokens" label="Token消耗" width="150" align="center" sortable>
          <template #default="{ row }">
            {{ formatNumber(row.total_tokens) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 表格区域 -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>最新接口使用记录</span>
          <el-button type="primary" link @click="$router.push('/admin/access-logs')">
            查看更多
          </el-button>
        </div>
      </template>
      <el-table :data="recentLogs" stripe>
        <el-table-column prop="user" label="用户" width="120">
          <template #default="{ row }">
            <span class="user-name">{{ row.username || '匿名' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="endpoint" label="API端点" min-width="200">
          <template #default="{ row }">
            <code class="endpoint-code">{{ row.endpoint || row.path }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="method" label="方法" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="getMethodType(row.method)">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status >= 200 && row.status < 300 ? 'success' : 'danger'">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="response_time" label="响应时间" width="100" align="center">
          <template #default="{ row }">
            {{ row.response_time }}ms
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import api from '@/stores'
import dayjs from 'dayjs'
import {
  User, Wallet, Connection, TrendCharts, Document, ArrowUp, Warning
} from '@element-plus/icons-vue'

const router = useRouter()
const chartDays = ref('7')
const trendChartRef = ref()
const pieChartRef = ref()
const errorChartRef = ref()
let trendChart = null
let pieChart = null
let errorChart = null

// 监听图表天数变化
watch(chartDays, () => {
  loadChartData()
})

const stats = reactive([
  { title: '总用户数', value: '0', icon: markRaw(User), bgColor: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { title: '总API数', value: '0', icon: markRaw(Connection), bgColor: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
  { title: '总请求数', value: '0', icon: markRaw(TrendCharts), bgColor: 'linear-gradient(135deg, #4ade80 0%, #22c55e 100%)' },
  { title: '本月消费', value: '¥0', icon: markRaw(Wallet), bgColor: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)' },
  { title: '今日Token', value: '0', icon: markRaw(Document), bgColor: 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)' },
  { title: '活跃用户', value: '0', icon: markRaw(Warning), bgColor: 'linear-gradient(135deg, #a855f7 0%, #9333ea 100%)' },
])

const recentLogs = ref([])
const trendData = ref([])
const distributionData = ref([])
const tokenStats = ref({})
const activeUsers = ref({})
const errorAnalysis = ref({})
const errorTrendData = ref([])

onMounted(async () => {
  await loadDashboardData()
  await loadChartData()
  initCharts()
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  trendChart?.dispose()
  pieChart?.dispose()
  errorChart?.dispose()
})

const resizeCharts = () => {
  trendChart?.resize()
  pieChart?.resize()
  errorChart?.resize()
}

const loadDashboardData = async () => {
  try {
    const [overview, logs, tokenRes, activeRes, errorRes] = await Promise.all([
      api.get('/dashboard/admin/overview/'),
      api.get('/proxy/access_logs/', { params: { page_size: 5 } }),
      api.get('/dashboard/admin/token-stats/'),
      api.get('/dashboard/admin/active-users/'),
      api.get('/dashboard/admin/error-analysis/', { params: { days: 7 } })
    ])

    stats[0].value = overview.total_users || 0
    stats[1].value = overview.total_apis || 0
    stats[2].value = overview.total_requests || 0
    stats[3].value = `¥${Number(overview.monthly_cost || 0).toFixed(2)}`
    stats[4].value = formatNumber(tokenRes.today?.total_tokens || 0)
    stats[5].value = activeRes.today_active || 0
    
    recentLogs.value = (logs.results || logs || []).map(log => ({
      ...log,
      username: log.username || '匿名',
      endpoint: log.endpoint_name || log.path
    }))
    
    tokenStats.value = tokenRes
    activeUsers.value = activeRes
    errorAnalysis.value = errorRes
    errorTrendData.value = errorRes.error_trend || []
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

const loadChartData = async () => {
  try {
    const days = parseInt(chartDays.value)
    const [trendRes, distRes] = await Promise.all([
      api.get('/dashboard/admin/trend/', { params: { days } }),
      api.get('/dashboard/admin/distribution/')
    ])
    
    trendData.value = trendRes || []
    distributionData.value = distRes || []
    
    updateCharts()
  } catch (error) {
    console.error('加载图表数据失败:', error)
  }
}

const updateCharts = () => {
  // 更新趋势图
  if (trendChart) {
    trendChart.setOption({
      xAxis: {
        data: trendData.value.map(d => d.date || d.date_str)
      },
      series: [{
        data: trendData.value.map(d => d.count || d.requests || 0)
      }]
    })
  }
  
  // 更新饼图
  if (pieChart) {
    const colors = ['#4ade80', '#f59e0b', '#667eea', '#f5576c', '#06b6d4', '#84cc16', '#a855f7', '#ec4899']
    pieChart.setOption({
      series: [{
        data: distributionData.value.map((d, i) => ({
          ...d,
          itemStyle: { color: colors[i % colors.length] }
        }))
      }]
    })
  }

  // 更新错误趋势图
  if (errorChart && errorTrendData.value.length > 0) {
    errorChart.setOption({
      xAxis: {
        data: errorTrendData.value.map(d => d.date)
      },
      series: [
        {
          name: '总请求',
          data: errorTrendData.value.map(d => d.total || 0)
        },
        {
          name: '错误数',
          data: errorTrendData.value.map(d => d.errors || 0)
        },
        {
          name: '错误率',
          data: errorTrendData.value.map(d => d.error_rate || 0)
        }
      ]
    })
  }
}

const initCharts = () => {
  // 趋势图
  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
      },
      yAxis: { type: 'value' },
      series: [{
        name: '请求数',
        type: 'line',
        smooth: true,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(74, 222, 128, 0.4)' },
            { offset: 1, color: 'rgba(74, 222, 128, 0.05)' }
          ])
        },
        lineStyle: { color: '#4ade80', width: 3 },
        itemStyle: { color: '#4ade80' },
        data: [820, 932, 901, 1234, 1290, 1330, 1520]
      }]
    })
  }

  // 饼图
  if (pieChartRef.value) {
    pieChart = echarts.init(pieChartRef.value)
    pieChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0, left: 'center' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold' }
        },
        data: [
          { value: 1048, name: 'ChatGPT', itemStyle: { color: '#4ade80' } },
          { value: 735, name: 'Claude', itemStyle: { color: '#f59e0b' } },
          { value: 580, name: 'Gemini', itemStyle: { color: '#667eea' } },
          { value: 484, name: '其他', itemStyle: { color: '#94a3b8' } }
        ]
      }]
    })
  }

  // 错误率趋势图
  if (errorChartRef.value) {
    errorChart = echarts.init(errorChartRef.value)
    errorChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: []
      },
      yAxis: [
        { type: 'value', name: '请求数' },
        { type: 'value', name: '错误率(%)', min: 0, max: 100 }
      ],
      series: [
        {
          name: '总请求',
          type: 'bar',
          yAxisIndex: 0,
          itemStyle: { color: '#667eea' },
          data: []
        },
        {
          name: '错误数',
          type: 'bar',
          yAxisIndex: 0,
          itemStyle: { color: '#f5576c' },
          data: []
        },
        {
          name: '错误率',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          lineStyle: { color: '#f59e0b', width: 2 },
          itemStyle: { color: '#f59e0b' },
          data: []
        }
      ]
    })
  }
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

const formatNumber = (num) => {
  if (!num || num === 0) return '0'
  if (num >= 100000000) return (num / 100000000).toFixed(2) + '亿'
  if (num >= 10000) return (num / 10000).toFixed(2) + '万'
  if (num >= 1000) return (num / 1000).toFixed(2) + 'K'
  return num.toString()
}

const getMethodType = (method) => {
  const types = { GET: '', POST: 'success', PUT: 'warning', DELETE: 'danger', PATCH: 'info' }
  return types[method] || ''
}
</script>

<style scoped>
.admin-dashboard {
  padding: 0;
  min-width: 0;
}

.quick-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.quick-actions .el-button {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.stat-title {
  font-size: 14px;
  color: #6b7280;
  margin-top: 4px;
}

/* 图表区域 */
.charts-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.chart-card {
  border-radius: 12px;
  min-width: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.chart-container {
  height: 280px;
}

/* 表格卡片 */
.table-card {
  border-radius: 12px;
}

.user-name {
  font-weight: 500;
  color: #374151;
}

.endpoint-code {
  font-size: 12px;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  color: #4f46e5;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .charts-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-bottom: 16px;
  }

  .stat-card {
    padding: 16px;
  }

  .stat-icon {
    width: 48px;
    height: 48px;
    font-size: 21px;
  }

  .stat-value {
    font-size: 24px;
  }

  .charts-row {
    gap: 16px;
    margin-bottom: 16px;
  }

  .card-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }

  .chart-container {
    height: 240px;
  }
}
</style>
