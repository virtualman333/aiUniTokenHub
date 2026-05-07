<template>
  <div class="usage-log">
    <!-- 头部 -->
    <div class="header">
      <h1>使用记录</h1>
      <p class="subtitle">查看您的 API 调用历史</p>
    </div>

    <!-- 查询表单 -->
    <el-card class="filter-card">
      <el-form inline :model="queryParams">
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="全部" clearable @change="handleQuery" style="width: 100px;">
            <el-option label="成功" value="success" />
            <el-option label="失败" value="error" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 日志列表 -->
    <el-card v-loading="loading">
      <el-table :data="logs" stripe>
        <el-table-column prop="path" label="API路径" min-width="180">
          <template #default="{ row }">
            <div class="path-cell">
              <el-tag size="small" :type="getMethodType(row.method)" effect="plain">
                {{ row.method }}
              </el-tag>
              <code class="endpoint-text">{{ row.path }}</code>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型" width="140">
          <template #default="{ row }">
            <span v-if="row.model_name">{{ row.model_name }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="response_status" label="状态码" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="getStatusType(row.response_status)"
              size="small"
            >
              {{ row.response_status || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Token (输入/输出/总)" width="170" align="center">
          <template #default="{ row }">
            <div v-if="row.total_tokens" class="tokens-cell">
              <span>{{ row.input_tokens || 0 }}</span>
              <span class="sep">/</span>
              <span>{{ row.output_tokens || 0 }}</span>
              <span class="sep">/</span>
              <strong>{{ row.total_tokens }}</strong>
              <el-tooltip
                v-if="Number(row.cached_tokens) > 0"
                :content="`缓存命中 ${row.cached_tokens} tokens`"
                placement="top"
              >
                <el-tag size="small" type="success" effect="plain" class="cache-tag">
                  缓存{{ row.cached_tokens }}
                </el-tag>
              </el-tooltip>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="费用" width="100" align="right">
          <template #default="{ row }">
            <span v-if="Number(row.cost) > 0" class="cost-cell">
              ¥{{ Number(row.cost).toFixed(4) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="response_time" label="响应时间" width="110" align="center">
          <template #default="{ row }">
            <span :class="getTimeClass(row.response_time)">
              {{ row.response_time ? row.response_time + 'ms' : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP地址" width="130" />
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="viewDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="handleQuery"
        @current-change="handleQuery"
        style="margin-top: 16px; justify-content: flex-end;"
      />

      <el-empty v-if="!loading && logs.length === 0" description="暂无记录" />
    </el-card>

    <!-- 详情弹窗 -->
    <LogDetailDialog
      v-model="showDetail"
      :log="currentLog"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import LogDetailDialog from './components/LogDetailDialog.vue'
import { useUsageLog } from './composables/useUsageLog'

const {
  loading,
  logs,
  pagination,
  queryParams,
  loadLogs,
  resetQuery: doResetQuery
} = useUsageLog()

const showDetail = ref(false)
const currentLog = ref<any>(null)

onMounted(() => {
  loadLogs()
})

function handleQuery() {
  pagination.page = 1
  loadLogs()
}

function resetQuery() {
  doResetQuery()
}

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

function viewDetail(row: any) {
  currentLog.value = row
  showDetail.value = true
}

function getStatusType(status: number) {
  if (!status) return 'info'
  if (status >= 200 && status < 300) return 'success'
  if (status >= 400 && status < 500) return 'warning'
  if (status >= 500) return 'danger'
  return 'info'
}

function getMethodType(method: string) {
  const types: Record<string, string> = {
    GET: '',
    POST: 'success',
    PUT: 'warning',
    DELETE: 'danger',
    PATCH: 'info'
  }
  return types[method] || ''
}

function getTimeClass(time: number) {
  if (!time) return ''
  if (time > 5000) return 'text-danger'
  if (time > 2000) return 'text-warning'
  return 'text-success'
}
</script>

<style scoped>
.usage-log {
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 24px;
}

.header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.filter-card {
  margin-bottom: 16px;
}

.path-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.endpoint-text {
  font-family: monospace;
  font-size: 13px;
  color: #409EFF;
}

.text-muted {
  color: #909399;
}

.tokens-cell {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: #475569;
}

.tokens-cell strong {
  color: #0f172a;
  font-weight: 600;
}

.tokens-cell .sep {
  color: #cbd5e1;
}

.tokens-cell .cache-tag {
  margin-left: 6px;
  transform: scale(0.92);
}

.cost-cell {
  color: #d97706;
  font-weight: 600;
  font-family: ui-monospace, monospace;
  font-size: 13px;
}

.text-success { color: #67C23A; }
.text-warning { color: #E6A23C; }
.text-danger { color: #F56C6C; }
</style>
