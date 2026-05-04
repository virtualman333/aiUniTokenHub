<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">访问日志</h2>
    </div>
    
    <el-card>
      <el-form inline :model="queryParams">
        <el-form-item label="API路径">
          <el-input v-model="queryParams.endpoint" placeholder="搜索路径" clearable @change="loadLogs" />
        </el-form-item>
        <el-form-item label="状态码">
          <el-input v-model="queryParams.status" placeholder="如: 200" clearable @change="loadLogs" />
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            @change="loadLogs"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadLogs">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
      
      <el-table :data="logs" v-loading="loading">
        <el-table-column prop="endpoint" label="API路径" min-width="200">
          <template #default="{ row }">
            <code>{{ row.endpoint }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="method" label="方法" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status_code" label="状态码" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status_code)" size="small">
              {{ row.status_code }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="response_time" label="响应时间" width="100" align="center">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.response_time > 1000 }">
              {{ row.response_time }}ms
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="user" label="用户" width="120">
          <template #default="{ row }">
            {{ row.user?.username || '公开' }}
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
            <el-button size="small" text @click="viewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadLogs"
        @current-change="loadLogs"
        style="margin-top: 16px; justify-content: flex-end;"
      />
    </el-card>
    
    <el-dialog v-model="showDetail" title="日志详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="API路径" :span="2">{{ currentLog?.endpoint }}</el-descriptions-item>
        <el-descriptions-item label="请求方法">{{ currentLog?.method }}</el-descriptions-item>
        <el-descriptions-item label="状态码">{{ currentLog?.status_code }}</el-descriptions-item>
        <el-descriptions-item label="响应时间">{{ currentLog?.response_time }}ms</el-descriptions-item>
        <el-descriptions-item label="用户">{{ currentLog?.user?.username || '公开' }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentLog?.ip_address }}</el-descriptions-item>
        <el-descriptions-item label="时间" :span="2">{{ formatDate(currentLog?.created_at) }}</el-descriptions-item>
      </el-descriptions>
      
      <div v-if="currentLog?.request_body" style="margin-top: 20px;">
        <h4>请求体</h4>
        <pre class="code-block">{{ currentLog.request_body }}</pre>
      </div>
      <div v-if="currentLog?.response_body" style="margin-top: 20px;">
        <h4>响应体</h4>
        <pre class="code-block">{{ currentLog.response_body }}</pre>
      </div>
      <div v-if="currentLog?.error_message" style="margin-top: 20px;">
        <h4>错误信息</h4>
        <pre class="code-block error">{{ currentLog.error_message }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/stores'
import dayjs from 'dayjs'

const logs = ref([])
const loading = ref(false)
const showDetail = ref(false)
const currentLog = ref(null)
const dateRange = ref([])

const queryParams = reactive({
  endpoint: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

onMounted(() => {
  loadLogs()
})

const loadLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (queryParams.endpoint) params.endpoint = queryParams.endpoint
    if (queryParams.status) params.status = queryParams.status
    if (dateRange.value?.length === 2) {
      params.start_date = dateRange.value[0].toISOString()
      params.end_date = dateRange.value[1].toISOString()
    }
    
    const res = await api.get('/proxy/access_logs/', { params })
    logs.value = res.results || res
    pagination.total = res.count || logs.value.length
  } catch (error) {
    ElMessage.error('加载日志失败')
  } finally {
    loading.value = false
  }
}

const resetQuery = () => {
  queryParams.endpoint = ''
  queryParams.status = ''
  dateRange.value = []
  pagination.page = 1
  loadLogs()
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const getStatusType = (status) => {
  if (status >= 200 && status < 300) return 'success'
  if (status >= 400 && status < 500) return 'warning'
  if (status >= 500) return 'danger'
  return 'info'
}

const viewDetail = (log) => {
  currentLog.value = log
  showDetail.value = true
}
</script>

<style lang="scss" scoped>
code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
}

.text-danger {
  color: #F56C6C;
}

.code-block {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  max-height: 200px;
  overflow: auto;
  
  &.error {
    color: #F56C6C;
  }
}
</style>
