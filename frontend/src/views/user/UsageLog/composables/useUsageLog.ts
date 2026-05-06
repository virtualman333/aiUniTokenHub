/**
 * 使用记录 Composable
 */
import { ref, reactive } from 'vue'
import api from '@/stores'

export interface UsageLog {
  id: number
  path: string
  method: string
  response_status: number
  response_time: number
  ip_address: string
  model_name?: string
  model_code?: string
  request_body?: string
  response_body?: string
  error_message?: string
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
  cached_tokens?: number
  cost?: number
  created_at: string
}

export function useUsageLog() {
  const loading = ref(false)
  const logs = ref<UsageLog[]>([])
  
  const pagination = reactive({
    page: 1,
    pageSize: 20,
    total: 0
  })

  const queryParams = reactive({
    status: ''
  })

  /**
   * 加载日志列表
   */
  async function loadLogs() {
    loading.value = true
    try {
      const params: Record<string, any> = {
        page: pagination.page,
        page_size: pagination.pageSize
      }
      
      if (queryParams.status) {
        params.status = queryParams.status
      }

      const res: any = await api.get('/users/usage-logs/', { params })
      logs.value = res.results || res || []
      pagination.total = res.count || res.total || logs.value.length
    } catch (e) {
      console.error('加载日志失败:', e)
      logs.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * 重置查询
   */
  function resetQuery() {
    queryParams.status = ''
    pagination.page = 1
    loadLogs()
  }

  return {
    loading,
    logs,
    pagination,
    queryParams,
    loadLogs,
    resetQuery
  }
}
