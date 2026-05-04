<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">使用记录</h2>
    </div>
    
    <el-card>
      <el-form inline :model="queryParams">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            @change="handleQuery"
          />
        </el-form-item>
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
      
      <el-table :data="logs" v-loading="loading">
        <el-table-column prop="endpoint" label="API路径" min-width="200">
          <template #default="{ row }">
            <span class="endpoint-text">{{ row.endpoint }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="method" label="方法" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status_code" label="状态码" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status_code >= 200 && row.status_code < 300 ? 'success' : 'danger'" size="small">
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
            <el-button size="small" text @click="viewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadLogs"
        @current-change="loadLogs"
        style="margin-top: 16px; justify-content: flex-end;"
      />
    </el-card>
    
    <!-- 详情对话框 -->
    <el-dialog v-model="showDetail" title="请求详情" width="600px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="API路径">{{ currentLog?.endpoint }}</el-descriptions-item>
        <el-descriptions-item label="请求方法">{{ currentLog?.method }}</el-descriptions-item>
        <el-descriptions-item label="状态码">{{ currentLog?.status_code }}</el-descriptions-item>
        <el-descriptions-item label="响应时间">{{ currentLog?.response_time }}ms</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentLog?.ip_address }}</el-descriptions-item>
        <el-descriptions-item label="时间">{{ formatDate(currentLog?.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <el-divider />
      <div v-if="currentLog?.request_body">
        <h4>请求体</h4>
        <pre class="detail-code">{{ currentLog.request_body }}</pre>
      </div>
      <div v-if="currentLog?.response_body">
        <h4>响应体</h4>
        <pre class="detail-code">{{ currentLog.response_body }}</pre>
      </div>
      <div v-if="currentLog?.error_message">
        <h4>错误信息</h4>
        <pre class="detail-code error">{{ currentLog.error_message }}</pre>
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
const dateRange = ref([])
const showDetail = ref(false)
const currentLog = ref(null)

const queryParams = reactive({
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
    
    if (dateRange.value?.length === 2) {
      params.start_date = dateRange.value[0].toISOString()
      params.end_date = dateRange.value[1].toISOString()
    }
    
    if (queryParams.status) {
      params.status = queryParams.status
    }
    
    const res = await api.get('/users/auth/me/', { params })
    // 这里需要根据实际API调整
    logs.value = []
    pagination.total = 0
  } catch (error) {
    ElMessage.error('加载记录失败')
  } finally {
    loading.value = false
  }
}

const handleQuery = () => {
  pagination.page = 1
  loadLogs()
}

const resetQuery = () => {
  queryParams.status = ''
  dateRange.value = []
  pagination.page = 1
  loadLogs()
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const viewDetail = (row) => {
  currentLog.value = row
  showDetail.value = true
}
</script>

<style lang="scss" scoped>
.endpoint-text {
  font-family: monospace;
  font-size: 13px;
}

.detail-code {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  max-height: 200px;
  
  &.error {
    color: #F56C6C;
  }
}
</style>
