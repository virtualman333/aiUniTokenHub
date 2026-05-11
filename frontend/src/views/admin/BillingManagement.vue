<template>
  <div class="billing-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>账单管理</h2>
      <span class="bill-count">共 {{ pagination.total }} 条记录</span>
    </div>

    <!-- 搜索栏 -->
    <el-card class="search-card">
      <el-form inline :model="queryParams">
        <el-form-item label="用户">
          <el-select
            v-model="queryParams.user"
            placeholder="全部用户"
            clearable
            filterable
            remote
            :remote-method="searchUsers"
            :loading="userLoading"
            style="width: 200px"
          >
            <el-option
              v-for="user in userOptions"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="queryParams.type" placeholder="全部" clearable>
            <el-option label="充值" value="recharge" />
            <el-option label="消费" value="consume" />
            <el-option label="退款" value="refund" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 280px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadBills">
            <Search /> 搜索
          </el-button>
          <el-button @click="resetQuery">
            <RefreshLeft /> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon recharge">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-label">总充值金额</div>
          <div class="stat-value">¥{{ stats.totalRecharge.toFixed(2) }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon consume">
          <el-icon><Money /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-label">总消费金额</div>
          <div class="stat-value">¥{{ stats.totalConsume.toFixed(2) }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon profit">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-label">总利润</div>
          <div class="stat-value" :class="{ 'negative': stats.totalProfit < 0 }">
            ¥{{ stats.totalProfit.toFixed(2) }}
          </div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon cost">
          <el-icon><Money /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-label">总上游成本</div>
          <div class="stat-value">¥{{ stats.totalUpstreamCost.toFixed(2) }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon count">
          <el-icon><Document /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-label">总记录数</div>
          <div class="stat-value">{{ stats.totalCount }}</div>
        </div>
      </div>
    </div>

    <!-- 账单表格 -->
    <el-card class="table-card">
      <el-table :data="bills" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        
        <el-table-column prop="username" label="用户" width="120">
          <template #default="{ row }">
            <div class="user-cell">
              <div class="user-avatar">{{ row.username?.[0]?.toUpperCase() || '?' }}</div>
              <span>{{ row.username || '未知' }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag 
              :type="row.type === 'recharge' ? 'success' : row.type === 'consume' ? 'warning' : 'danger'" 
              size="small" 
              round
            >
              {{ row.type_display }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="amount" label="金额" width="120" align="right">
          <template #default="{ row }">
            <span :class="['amount', row.type]">
              {{ row.type === 'consume' ? '-' : '+' }}¥{{ Number(row.amount || 0).toFixed(4) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="upstream_cost" label="上游成本" width="120" align="right">
          <template #default="{ row }">
            <span v-if="row.type === 'consume'" class="upstream-cost">
              ¥{{ Number(row.upstream_cost || 0).toFixed(4) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="profit" label="利润" width="120" align="right">
          <template #default="{ row }">
            <span v-if="row.type === 'consume'" :class="['profit', { negative: row.profit < 0 }]">
              ¥{{ Number(row.profit || 0).toFixed(4) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="balance" label="余额" width="120" align="right">
          <template #default="{ row }">
            <span class="balance">¥{{ Number(row.balance || 0).toFixed(4) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
        
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @change="loadBills"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { Search, RefreshLeft, TrendCharts, Money, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/stores'

// 查询参数
const queryParams = reactive({
  user: null,
  type: '',
  start_date: '',
  end_date: '',
})

const dateRange = ref(null)
const bills = ref([])
const loading = ref(false)
const userOptions = ref([])
const userLoading = ref(false)

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

// 统计数据
const stats = reactive({
  totalRecharge: 0,
  totalConsume: 0,
  totalProfit: 0,
  totalUpstreamCost: 0,
  totalCount: 0,
})

// 加载账单列表
const loadBills = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }

    if (queryParams.user) params.user = queryParams.user
    if (queryParams.type) params.type = queryParams.type
    if (dateRange.value && dateRange.value[0]) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }

    const res = await api.get('/users/billing/admin-bills/', { params })
    // API 拦截器已处理统一响应格式，res 直接是 data 部分
    if (res && res.results) {
      bills.value = res.results || []
      pagination.total = res.total || 0

      // 使用服务端返回的利润汇总
      stats.totalRecharge = 0
      stats.totalConsume = res.total_revenue || 0
      stats.totalProfit = res.total_profit || 0
      stats.totalUpstreamCost = res.total_upstream_cost || 0
      stats.totalCount = res.total || 0

      // 补充计算当前页充值金额
      bills.value.forEach(bill => {
        if (bill.type === 'recharge') {
          stats.totalRecharge += Number(bill.amount || 0)
        }
      })
    }
  } catch (error) {
    console.error('加载账单失败:', error)
    ElMessage.error('加载账单失败')
  } finally {
    loading.value = false
  }
}

// 搜索用户
const searchUsers = async (query) => {
  if (!query) {
    userOptions.value = []
    return
  }
  
  userLoading.value = true
  try {
    const res = await api.get('/dashboard/admin/users/', {
      params: { search: query, page: 1, page_size: 10 }
    })
    // API 拦截器已处理，res 直接是 data 部分
    if (res && res.results) {
      userOptions.value = res.results || []
    }
  } catch (error) {
    console.error('搜索用户失败:', error)
  } finally {
    userLoading.value = false
  }
}

// 重置查询
const resetQuery = () => {
  queryParams.user = null
  queryParams.type = ''
  dateRange.value = null
  pagination.page = 1
  userOptions.value = []
  loadBills()
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

onMounted(() => {
  loadBills()
})
</script>

<style scoped>
.billing-management {
  min-width: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: #1f2937;
}

.bill-count {
  font-size: 14px;
  color: #6b7280;
}

.search-card {
  margin-bottom: 20px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
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
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-icon.recharge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.stat-icon.consume {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: #fff;
}

.stat-icon.profit {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: #fff;
}

.stat-icon.cost {
  background: linear-gradient(135deg, #fc5c7d 0%, #6a82fb 100%);
  color: #fff;
}

.stat-icon.count {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: #fff;
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.table-card {
  margin-bottom: 20px;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.amount {
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.amount.recharge {
  color: #10b981;
}

.amount.consume {
  color: #f59e0b;
}

.amount.refund {
  color: #ef4444;
}

.upstream-cost {
  font-weight: 500;
  font-family: 'Courier New', monospace;
  color: #6b7280;
}

.profit {
  font-weight: 600;
  font-family: 'Courier New', monospace;
  color: #10b981;
}

.profit.negative {
  color: #ef4444;
}

.stat-value.negative {
  color: #ef4444;
}

.balance {
  font-weight: 500;
  font-family: 'Courier New', monospace;
  color: #374151;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
