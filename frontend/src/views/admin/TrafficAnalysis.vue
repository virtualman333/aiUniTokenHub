<template>
  <div class="traffic-analysis">
    <!-- 统计卡片 -->
    <div class="stats-row">
      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #667eea, #764ba2)">
          <el-icon :size="24"><Document /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_pv }}</div>
          <div class="stat-label">总 PV</div>
        </div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #43e97b, #38f9d7)">
          <el-icon :size="24"><User /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_uv }}</div>
          <div class="stat-label">总 UV</div>
        </div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb, #f5576c)">
          <el-icon :size="24"><Location /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_ips }}</div>
          <div class="stat-label">独立 IP</div>
        </div>
      </el-card>
    </div>

    <!-- 筛选栏 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <span>筛选条件</span>
      </template>
      <el-form :inline="true" :model="filters" @submit.prevent="handleSearch">
        <el-form-item label="网页路径">
          <el-input
            v-model="filters.path"
            placeholder="请输入路径，如 /admin/dashboard"
            clearable
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item label="IP 地址">
          <el-input
            v-model="filters.ip_address"
            placeholder="请输入 IP 地址"
            clearable
            style="width: 180px"
          />
        </el-form-item>
        <el-form-item label="访问时间">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><RefreshRight /></el-icon>重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 记录表格 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <div class="table-header">
          <span>访问记录</span>
          <span class="record-count">共 {{ total }} 条</span>
        </div>
      </template>
      <el-table :data="records" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="path" label="访问路径" min-width="220" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP 地址" width="150" align="center" />
        <el-table-column prop="username" label="用户" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.username === '匿名' ? 'info' : 'success'" size="small">
              {{ row.username }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="referer" label="来源页" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.referer">{{ row.referer }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="访问时间" width="180" align="center" />
      </el-table>

      <div class="pagination" style="margin-top: 20px; display: flex; justify-content: center">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchRecords"
          @current-change="fetchRecords"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, RefreshRight, Document, User, Location } from '@element-plus/icons-vue'
import api from '@/stores'

// 统计数据
const stats = ref({
  total_pv: 0,
  total_uv: 0,
  total_ips: 0,
})

// 筛选条件
const filters = reactive({
  path: '',
  ip_address: '',
  dateRange: null,
})

// 表格数据
const records = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 构建查询参数
function buildParams() {
  const params = {
    page: page.value,
    page_size: pageSize.value,
  }
  if (filters.path) params.path = filters.path
  if (filters.ip_address) params.ip_address = filters.ip_address
  if (filters.dateRange && filters.dateRange.length === 2) {
    params.start_date = filters.dateRange[0]
    params.end_date = filters.dateRange[1]
  }
  return params
}

// 获取记录数据
async function fetchRecords() {
  loading.value = true
  try {
    const res = await api.get('/api/admin/analytics/records/', {
      params: buildParams(),
    })
    records.value = res.data || []
    stats.value.total_pv = res.total_pv || 0
    stats.value.total_uv = res.total_uv || 0
    stats.value.total_ips = res.total_ips || 0
    total.value = res.total || 0
  } catch (error) {
    ElMessage.error('获取访问记录失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 搜索
function handleSearch() {
  page.value = 1
  fetchRecords()
}

// 重置筛选
function handleReset() {
  filters.path = ''
  filters.ip_address = ''
  filters.dateRange = null
  page.value = 1
  fetchRecords()
}

onMounted(() => {
  fetchRecords()
})
</script>

<style scoped>
.traffic-analysis {
  padding: 20px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
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
  font-size: 24px;
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

.record-count {
  font-size: 13px;
  color: #909399;
  font-weight: 400;
}

.text-muted {
  color: #c0c4cc;
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
}
</style>
