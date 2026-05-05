/**
 * 控制台 Composable
 */
import { ref } from 'vue'
import api from '@/stores'

export function useDashboard() {
  const loading = ref(false)
  const overview = ref({
    total_requests: 0,
    today_requests: 0,
    success_rate: 100,
    avg_response_time: 0
  })
  const topAPIs = ref([])
  const requestStats = ref([])

  /**
   * 获取概览数据
   */
  async function fetchOverview() {
    try {
      const res = await api.get('/dashboard/user/overview/')
      overview.value = res
    } catch (e) {
      console.error('获取概览失败:', e)
    }
  }

  /**
   * 获取热门API
   */
  async function fetchTopAPIs(limit = 5) {
    try {
      const res = await api.get('/dashboard/user/top-apis/', { params: { limit } })
      topAPIs.value = res.results || res || []
    } catch (e) {
      console.error('获取热门API失败:', e)
    }
  }

  /**
   * 获取请求统计
   */
  async function fetchRequestStats(days = 7) {
    try {
      const res = await api.get('/dashboard/user/request-stats/', { params: { days } })
      requestStats.value = res.results || res || []
    } catch (e) {
      console.error('获取请求统计失败:', e)
    }
  }

  /**
   * 加载所有数据
   */
  async function loadData() {
    loading.value = true
    try {
      await Promise.all([
        fetchOverview(),
        fetchTopAPIs(),
        fetchRequestStats()
      ])
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    overview,
    topAPIs,
    requestStats,
    fetchOverview,
    fetchTopAPIs,
    fetchRequestStats,
    loadData
  }
}
