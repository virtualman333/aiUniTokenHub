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
          <el-select v-model="queryParams.status" placeholder="全部" clearable @change="handleQuery">
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
      <el-table :data="logs">
        <el-table-column prop="endpoint" label="API路径" min-width="200">
          <template #default="{ row }">
            <code class="endpoint-text">{{ row.endpoint }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="method" label="方法" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status_code" label="状态码" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.status_code >= 200 && row.status_code < 300 ? 'success' : 'danger'"
              size="small"
            >
              {{ row.status_code }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="response_time" label="响应时间" width="100" align="center">
          <template #default="{ row }">
            {{ row.response_time }}ms
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP地址" width="140" />
        <el-table-column prop="created_at" label="时间" width="180">
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

.endpoint-text {
  font-family: monospace;
  font-size: 13px;
  color: #409EFF;
}
</style>
