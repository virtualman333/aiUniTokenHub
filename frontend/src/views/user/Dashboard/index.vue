<template>
  <div class="dashboard">
    <!-- 头部 -->
    <div class="header">
      <h1>控制台</h1>
      <p class="subtitle">查看您的 API 使用概览</p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <StatCard
          :value="overview.total_requests || 0"
          label="总请求数"
          gradient="linear-gradient(135deg, #409EFF, #66b1ff)"
        />
      </el-col>
      <el-col :span="6">
        <StatCard
          :value="overview.today_requests || 0"
          label="今日请求"
          gradient="linear-gradient(135deg, #67C23A, #85ce61)"
        />
      </el-col>
      <el-col :span="6">
        <StatCard
          :value="`${overview.success_rate || 100}%`"
          label="成功率"
          gradient="linear-gradient(135deg, #E6A23C, #ebb563)"
        />
      </el-col>
      <el-col :span="6">
        <StatCard
          :value="`${overview.avg_response_time || 0}ms`"
          label="平均响应时间"
          gradient="linear-gradient(135deg, #909399, #a6a9ad)"
        />
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" v-loading="loading">
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <span class="card-title">请求趋势</span>
          </template>
          <RequestChart :data="requestStats" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <span class="card-title">热门API</span>
          </template>
          <el-table :data="topAPIs" size="small">
            <el-table-column prop="name" label="API名称" />
            <el-table-column prop="count" label="调用次数" width="100" align="right" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import StatCard from './components/StatCard.vue'
import RequestChart from './components/RequestChart.vue'
import { useDashboard } from './composables/useDashboard'

const {
  loading,
  overview,
  topAPIs,
  requestStats,
  loadData
} = useDashboard()

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
  font-size: 16px;
}

.stat-row {
  margin-bottom: 24px;
}

.chart-card {
  height: 100%;
}

.card-title {
  font-weight: 600;
  font-size: 16px;
}
</style>
