<template>
  <div class="traffic-analysis">
    <!-- 统计卡片 -->
    <div class="stats-row">
      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #667eea, #764ba2)">
          <el-icon :size="24"><Document /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ summary.today.pv }}</div>
          <div class="stat-label">今日 PV</div>
        </div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #43e97b, #38f9d7)">
          <el-icon :size="24"><User /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ summary.today.uv }}</div>
          <div class="stat-label">今日 UV</div>
        </div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb, #f5576c)">
          <el-icon :size="24"><Location /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ summary.today.ips }}</div>
          <div class="stat-label">今日独立 IP</div>
        </div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #4facfe, #00f2fe)">
          <el-icon :size="24"><TrendCharts /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ summary.total.pv }}</div>
          <div class="stat-label">累计总 PV</div>
        </div>
      </el-card>
    </div>

    <!-- 操作栏 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <div class="table-header">
          <span>每日访问统计</span>
          <el-radio-group v-model="days" size="small" @change="fetchData">
            <el-radio-button :value="7">近 7 天</el-radio-button>
            <el-radio-button :value="15">近 15 天</el-radio-button>
            <el-radio-button :value="30">近 30 天</el-radio-button>
            <el-radio-button :value="90">近 90 天</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-table :data="dailyList" stripe v-loading="loading" show-summary :summary-method="getSummaryRow">
        <el-table-column prop="date" label="日期" width="120" align="center" fixed />
        <el-table-column prop="pv" label="PV（页面浏览）" min-width="140" align="center" sortable>
          <template #default="{ row }">
            <span class="num-pv">{{ row.pv.toLocaleString() }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="uv" label="UV（访客数）" min-width="130" align="center" sortable>
          <template #default="{ row }">
            <span class="num-uv">{{ row.uv.toLocaleString() }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="ips" label="独立 IP 数" min-width="120" align="center" sortable>
          <template #default="{ row }">
            <span class="num-ip">{{ row.ips.toLocaleString() }}</span>
          </template>
        </el-table-column>
        <el-table-column label="人均浏览" width="110" align="center">
          <template #default="{ row }">
            {{ row.uv > 0 ? (row.pv / row.uv).toFixed(1) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="环比昨日" width="100" align="center">
          <template #default="{ $index }">
            <template v-if="$index === 0">-</template>
            <span v-else-if="dailyList[$index - 1].pv === 0" class="text-muted">-</span>
            <span v-else :class="row.pv >= dailyList[$index - 1].pv ? 'text-up' : 'text-down'">
              {{ ((row.pv - dailyList[$index - 1].pv) / dailyList[$index - 1].pv * 100).toFixed(1) }}%
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, User, Location, TrendCharts } from '@element-plus/icons-vue'
import api from '@/stores'

// 概览数据
const summary = reactive({
  today: { pv: 0, uv: 0, ips: 0 },
  total: { pv: 0, uv: 0, ips: 0 },
})

// 表格数据
const days = ref(30)
const loading = ref(false)
const dailyList = ref([])

// 获取概览 + 趋势
async function fetchData() {
  loading.value = true
  try {
    const [sumRes, trendRes] = await Promise.all([
      api.get('/dashboard/admin/analytics/summary/'),
      api.get('/dashboard/admin/analytics/trend/', { params: { days: days.value } }),
    ])
    Object.assign(summary.today, sumRes.today || {})
    Object.assign(summary.total, sumRes.total || {})
    // 响应拦截器解包后 trendRes 即为 data 数组
    dailyList.value = Array.isArray(trendRes) ? trendRes : []
  } catch (error) {
    ElMessage.error('获取流量数据失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 合计行
function getSummaryRow({ columns }) {
  const sums = []
  columns.forEach((col, i) => {
    if (i === 0) { sums[i] = '合计'; return }
    if (col.property === 'pv') { sums[i] = dailyList.value.reduce((s, r) => s + r.pv, 0); return }
    if (col.property === 'uv') { sums[i] = dailyList.value.reduce((s, r) => s + r.uv, 0); return }
    if (col.property === 'ips') { sums[i] = dailyList.value.reduce((s, r) => s + r.ips, 0); return }
    if (col.property === '人均浏览') {
      const tPv = dailyList.value.reduce((s, r) => s + r.pv, 0)
      const tUv = dailyList.value.reduce((s, r) => s + r.uv, 0)
      sums[i] = tUv > 0 ? (tPv / tUv).toFixed(1) : '-'
      return
    }
    sums[i] = ''
  })
  return sums
}

onMounted(() => fetchData())
</script>

<style scoped>
.traffic-analysis {
  padding: 20px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  border-radius: 12px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #6b7280;
  margin-top: 4px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.num-pv { font-weight: 600; color: #667eea; }
.num-uv { font-weight: 600; color: #43e97b; }
.num-ip { font-weight: 600; color: #f093fb; }

.text-up { color: #67c23a; font-weight: 600; }
.text-down { color: #f56c6c; font-weight: 600; }
.text-muted { color: #c0c4cc; }

@media (max-width: 1024px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 560px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
}
</style>
