<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">接口使用记录</h2>
      <div class="header-actions">
        <el-button @click="loadLogs">
          <RefreshLeft /> 刷新
        </el-button>
        <el-button type="primary" @click="exportLogs">
          <Download /> 导出
        </el-button>
      </div>
    </div>

    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value">{{ stats.total }}</div>
            <div class="stat-label">总请求数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value text-success">{{ stats.success }}</div>
            <div class="stat-label">成功请求</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value text-danger">{{ stats.failed }}</div>
            <div class="stat-label">失败请求</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value">{{ stats.avgTime }}ms</div>
            <div class="stat-label">平均响应时间</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-card>
      <el-form inline :model="queryParams" class="filter-form">
        <el-form-item label="API路径">
          <el-input 
            v-model="queryParams.path" 
            placeholder="搜索路径" 
            clearable 
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item label="请求方法">
          <el-select v-model="queryParams.method" placeholder="全部" clearable style="width: 100px">
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
            <el-option label="PUT" value="PUT" />
            <el-option label="DELETE" value="DELETE" />
            <el-option label="PATCH" value="PATCH" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态码">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="2xx 成功" value="2xx" />
            <el-option label="4xx 客户端错误" value="4xx" />
            <el-option label="5xx 服务端错误" value="5xx" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户">
          <el-input 
            v-model="queryParams.username" 
            placeholder="用户名" 
            clearable 
            style="width: 120px"
          />
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 260px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <Search /> 查询
          </el-button>
          <el-button @click="resetQuery">
            <RefreshLeft /> 重置
          </el-button>
        </el-form-item>
      </el-form>
      
      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column prop="path" label="API路径" min-width="180">
          <template #default="{ row }">
            <div class="path-cell">
              <el-tag size="small" :type="getMethodType(row.method)" effect="plain">
                {{ row.method }}
              </el-tag>
              <code class="path-code">{{ row.path }}</code>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型" width="150">
          <template #default="{ row }">
            <span v-if="row.model_name">{{ row.model_name }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="upstream_account_name" label="上游账号" width="150">
          <template #default="{ row }">
            <div v-if="row.upstream_account_name">
              <span>{{ row.upstream_account_name }}</span>
              <br>
              <span class="text-muted" style="font-size: 12px">{{ row.upstream_provider }}</span>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="response_status" label="状态码" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.response_status)" size="small">
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
                :content="`其中缓存命中 ${row.cached_tokens} tokens`"
                placement="top"
              >
                <el-tag size="small" type="success" effect="plain" class="cache-tag">
                  缓存 {{ row.cached_tokens }}
                </el-tag>
              </el-tooltip>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="费用" width="110" align="right">
          <template #default="{ row }">
            <span v-if="Number(row.cost) > 0" class="cost-cell">
              ¥{{ Number(row.cost).toFixed(4) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="response_time" label="响应时间" width="120" align="center">
          <template #default="{ row }">
            <span :class="getTimeClass(row.response_time)">
              {{ row.response_time ? row.response_time + 'ms' : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户" width="100">
          <template #default="{ row }">
            {{ row.username || '匿名' }}
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP地址" width="130" />
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="viewDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadLogs"
          @current-change="loadLogs"
        />
      </div>
    </el-card>
    
    <el-dialog v-model="showDetail" title="使用详情" width="800px" destroy-on-close>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="API路径" :span="2">
          <code>{{ currentLog?.path }}</code>
        </el-descriptions-item>
        <el-descriptions-item label="请求方法">
          <el-tag size="small" :type="getMethodType(currentLog?.method)">
            {{ currentLog?.method }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态码">
          <el-tag :type="getStatusType(currentLog?.response_status)" size="small">
            {{ currentLog?.response_status || '-' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="响应时间">
          {{ currentLog?.response_time ? currentLog?.response_time + 'ms' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="用户">
          {{ currentLog?.username || '匿名' }}
        </el-descriptions-item>
        <el-descriptions-item label="IP地址">
          {{ currentLog?.ip_address || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="访问时间">
          {{ formatDate(currentLog?.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="Tokens (输入/输出/总)">
          <span v-if="currentLog?.total_tokens">
            {{ currentLog?.input_tokens || 0 }} / {{ currentLog?.output_tokens || 0 }} /
            <strong>{{ currentLog?.total_tokens }}</strong>
            <span v-if="Number(currentLog?.cached_tokens) > 0" class="text-muted" style="margin-left: 6px;">
              （缓存 {{ currentLog?.cached_tokens }}）
            </span>
          </span>
          <span v-else class="text-muted">-</span>
        </el-descriptions-item>
        <el-descriptions-item label="费用">
          <strong v-if="Number(currentLog?.cost) > 0" style="color: #d97706">
            ¥{{ Number(currentLog?.cost).toFixed(6) }}
          </strong>
          <span v-else class="text-muted">-</span>
        </el-descriptions-item>
      </el-descriptions>
      
      <div v-if="currentLog?.request_body" class="detail-section">
        <div class="section-header">
          <h4>请求体</h4>
          <el-button size="small" text @click="copyToClipboard(currentLog?.request_body)">
            <CopyDocument /> 复制
          </el-button>
        </div>
        <pre class="code-block">{{ formatJson(currentLog?.request_body) }}</pre>
      </div>
      
      <div v-if="currentLog?.response_body" class="detail-section">
        <div class="section-header">
          <h4>响应体</h4>
          <el-button size="small" text @click="copyToClipboard(currentLog?.response_body)">
            <CopyDocument /> 复制
          </el-button>
        </div>
        <pre class="code-block">{{ formatJson(currentLog?.response_body) }}</pre>
      </div>
      
      <div v-if="currentLog?.error_message" class="detail-section">
        <div class="section-header">
          <h4>错误信息</h4>
        </div>
        <pre class="code-block error">{{ currentLog?.error_message }}</pre>
      </div>

      <div v-if="currentLog?.request_params && Object.keys(currentLog?.request_params || {}).length" class="detail-section">
        <div class="section-header">
          <h4>请求参数</h4>
        </div>
        <pre class="code-block">{{ JSON.stringify(currentLog?.request_params, null, 2) }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, RefreshLeft, Download, CopyDocument } from '@element-plus/icons-vue'
import api from '@/stores'
import dayjs from 'dayjs'
import { copyToClipboard as clipboardCopy } from '@/utils/clipboard'

const logs = ref([])
const loading = ref(false)
const showDetail = ref(false)
const currentLog = ref(null)
const dateRange = ref([])
let refreshTimer = null

const queryParams = reactive({
  path: '',
  method: '',
  status: '',
  username: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const stats = computed(() => {
  const total = logs.value.length
  const success = logs.value.filter(l => l.response_status >= 200 && l.response_status < 300).length
  const failed = logs.value.filter(l => l.response_status >= 400).length
  const avgTime = total > 0 
    ? Math.round(logs.value.reduce((sum, l) => sum + (l.response_time || 0), 0) / total)
    : 0
  
  return { total: pagination.total, success, failed, avgTime }
})

onMounted(() => {
  loadLogs()
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})

const loadLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (queryParams.path) params.path = queryParams.path
    if (queryParams.method) params.method = queryParams.method
    if (queryParams.username) params.username = queryParams.username
    if (queryParams.status) {
      if (queryParams.status === '2xx') params.status_gte = 200, params.status_lt = 300
      else if (queryParams.status === '4xx') params.status_gte = 400, params.status_lt = 500
      else if (queryParams.status === '5xx') params.status_gte = 500, params.status_lt = 600
    }
    if (dateRange.value?.length === 2) {
      params.start_date = dayjs(dateRange.value[0]).startOf('day').toISOString()
      params.end_date = dayjs(dateRange.value[1]).endOf('day').toISOString()
    }
    
    const res = await api.get('/proxy/access_logs/', { params })
    logs.value = res.results || res
    pagination.total = res.count || logs.value.length
  } catch (error) {
    ElMessage.error('加载日志失败: ' + (error.message || ''))
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadLogs()
}

const resetQuery = () => {
  queryParams.path = ''
  queryParams.method = ''
  queryParams.status = ''
  queryParams.username = ''
  dateRange.value = []
  pagination.page = 1
  loadLogs()
}

const exportLogs = async () => {
  try {
    const params = { ...queryParams }
    if (dateRange.value?.length === 2) {
      params.start_date = dayjs(dateRange.value[0]).startOf('day').toISOString()
      params.end_date = dayjs(dateRange.value[1]).endOf('day').toISOString()
    }
    
    const res = await api.get('/proxy/access_logs/', { params: { ...params, page_size: 1000 } })
    const data = res.results || res
    
    if (!data.length) {
      ElMessage.warning('没有数据可导出')
      return
    }
    
    const csv = [
      ['时间', '路径', '方法', '状态码', '响应时间(ms)', '输入Token', '输出Token', '总Token', '缓存Token', '费用(元)', '用户', 'IP地址'].join(','),
      ...data.map(log => [
        formatDate(log.created_at),
        log.path,
        log.method,
        log.response_status || '-',
        log.response_time || '-',
        log.input_tokens || 0,
        log.output_tokens || 0,
        log.total_tokens || 0,
        log.cached_tokens || 0,
        Number(log.cost || 0).toFixed(6),
        log.username || '匿名',
        log.ip_address || '-'
      ].join(','))
    ].join('\n')
    
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `usage_logs_${dayjs().format('YYYYMMDD_HHmmss')}.csv`
    link.click()
    URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

const formatDate = (date) => {
  return date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const getStatusType = (status) => {
  if (!status) return 'info'
  if (status >= 200 && status < 300) return 'success'
  if (status >= 400 && status < 500) return 'warning'
  if (status >= 500) return 'danger'
  return 'info'
}

const getMethodType = (method) => {
  const types = {
    GET: '',
    POST: 'success',
    PUT: 'warning',
    DELETE: 'danger',
    PATCH: 'info'
  }
  return types[method] || ''
}

const getTimeClass = (time) => {
  if (!time) return ''
  if (time > 1000) return 'text-danger'
  if (time > 500) return 'text-warning'
  return 'text-success'
}

const viewDetail = (log) => {
  currentLog.value = log
  showDetail.value = true
}

const decodeUnicode = (str) => {
  if (!str) return ''
  return str.replace(/\\u([\dA-Fa-f]{4})/g, (match, p1) => {
    return String.fromCharCode(parseInt(p1, 16))
  })
}

const formatJson = (str) => {
  if (!str) return ''
  try {
    const decoded = decodeUnicode(str)
    return JSON.stringify(JSON.parse(decoded), null, 2)
  } catch {
    return decodeUnicode(str)
  }
}

const copyToClipboard = async (text) => {
  const success = await clipboardCopy(text)
  if (success) {
    ElMessage.success('已复制到剪贴板')
  } else {
    ElMessage.error('复制失败')
  }
}
</script>

<style lang="scss" scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
  padding: 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409EFF;
  
  &.text-success { color: #67C23A; }
  &.text-danger { color: #F56C6C; }
}

.stat-label {
  margin-top: 8px;
  color: #909399;
  font-size: 14px;
}

.filter-form {
  margin-bottom: 16px;
}

.path-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.path-code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
  font-family: monospace;
}

.tokens-cell {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: #475569;

  strong {
    color: #0f172a;
    font-weight: 600;
  }

  .sep {
    color: #cbd5e1;
  }

  .cache-tag {
    margin-left: 6px;
    transform: scale(0.92);
  }
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
.text-muted { color: #909399; font-size: 12px; }

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-section {
  margin-top: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  
  h4 {
    margin: 0;
    font-size: 14px;
    color: #606266;
  }
}

.code-block {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  max-height: 300px;
  overflow: auto;
  font-family: monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  
  &.error {
    color: #F56C6C;
    background: #fef0f0;
  }
}
</style>
