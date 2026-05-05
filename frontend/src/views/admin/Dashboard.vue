<template>
  <div class="admin-dashboard">
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

    <!-- 表格区域 -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>最新访问日志</span>
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
import { ref, reactive, onMounted, onUnmounted, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import api from '@/stores'
import dayjs from 'dayjs'
import {
  User, Money, Connection, TrendCharts, Document, Top, Warning
} from '@element-plus/icons-vue'

const router = useRouter()
const chartDays = ref('7')
const trendChartRef = ref()
const pieChartRef = ref()
let trendChart = null
let pieChart = null

const stats = reactive([
  { title: '总用户数', value: '0', icon: markRaw(User), bgColor: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { title: '总API数', value: '0', icon: markRaw(Connection), bgColor: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
  { title: '总请求数', value: '0', icon: markRaw(TrendCharts), bgColor: 'linear-gradient(135deg, #4ade80 0%, #22c55e 100%)' },
  { title: '本月消费', value: '¥0', icon: markRaw(Money), bgColor: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)' },
])

const recentLogs = ref([])

onMounted(async () => {
  await loadDashboardData()
  initCharts()
})

onUnmounted(() => {
  trendChart?.dispose()
  pieChart?.dispose()
})

const loadDashboardData = async () => {
  try {
    const [overview, logs] = await Promise.all([
      api.get('/dashboard/overview/'),
      api.get('/proxy/forward/access_logs/', { params: { page_size: 5 } })
    ])

    stats[0].value = overview.total_users || 0
    stats[1].value = overview.total_apis || 0
    stats[2].value = overview.total_requests || 0
    stats[3].value = `¥${Number(overview.monthly_cost || 0).toFixed(2)}`
    
    recentLogs.value = (logs.results || logs || []).map(log => ({
      ...log,
      username: log.username || '匿名',
      endpoint: log.endpoint_name || log.path
    }))
  } catch (error) {
    console.error('加载数据失败:', error)
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
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

const getMethodType = (method) => {
  const types = { GET: '', POST: 'success', PUT: 'warning', DELETE: 'danger', PATCH: 'info' }
  return types[method] || ''
}
</script>

<style scoped>
.admin-dashboard {
  padding: 0;
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
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.2;
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
</style>
