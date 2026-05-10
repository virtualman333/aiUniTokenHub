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
    total_input_tokens: 0,
    total_output_tokens: 0,
    total_tokens: 0
  })
  const topModels = ref([])
  const requestStats = ref([])
  const inviteInfo = ref({
    invite_code: '',
    invite_count: 0,
    total_reward: 0,
    config: {
      rebate_type: 'first',
      rebate_type_display: '首次返利',
      rebate_ratio: 0.1,
      upgrade_threshold: 10,
      reward_threshold: 100,
      rebate_description: ''
    }
  })
  const inviteRewards = ref([])

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
   * 获取热门模型
   */
  async function fetchTopModels(limit = 5) {
    try {
      const res = await api.get('/dashboard/user/top-models/', { params: { limit } })
      topModels.value = res.results || res || []
    } catch (e) {
      console.error('获取热门模型失败:', e)
      // 如果后端接口还未实现，使用模拟数据
      topModels.value = [
        { name: 'gpt-4o', count: 1250, success_rate: 99.2 },
        { name: 'claude-3-5-sonnet', count: 980, success_rate: 98.8 },
        { name: 'gemini-2.0-flash', count: 756, success_rate: 99.5 },
        { name: 'gpt-4o-mini', count: 620, success_rate: 99.8 },
        { name: 'qwen-turbo', count: 430, success_rate: 99.1 }
      ].slice(0, limit)
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
   * 获取邀请信息
   */
  async function fetchInviteInfo() {
    try {
      const res = await api.get('/users/invite/info/')
      inviteInfo.value = res
    } catch (e) {
      console.error('获取邀请信息失败:', e)
    }
  }

  /**
   * 获取邀请收益记录
   */
  async function fetchInviteRewards() {
    try {
      const res = await api.get('/users/invite/rewards/')
      inviteRewards.value = res || []
    } catch (e) {
      console.error('获取邀请收益失败:', e)
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
        fetchTopModels(),
        fetchRequestStats(),
        fetchInviteInfo(),
        fetchInviteRewards()
      ])
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    overview,
    topModels,
    requestStats,
    inviteInfo,
    inviteRewards,
    fetchOverview,
    fetchTopModels,
    fetchRequestStats,
    fetchInviteInfo,
    fetchInviteRewards,
    loadData
  }
}
