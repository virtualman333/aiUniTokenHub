/**
 * 账单中心 Composable
 */
import { ref, reactive } from 'vue'
import api from '@/stores'

export interface Bill {
  id: number
  type: 'recharge' | 'consume' | 'refund' | 'bonus'
  amount: number
  balance: number
  description: string
  created_at: string
}

/** 余额续航：按最近一段时间的消耗速度估算余额还能撑多久 */
export interface Runway {
  balance: number
  /** 实际参与计算的窗口天数（账号太新时会小于 7） */
  window_days: number
  /** 窗口内有消耗的天数 */
  active_days: number
  avg_daily_cost: number
  /** 还能用几天；null 表示算不出来（余额已空或窗口内无消耗） */
  runway_days: number | null
  exhaust_date: string | null
  level: 'empty' | 'idle' | 'critical' | 'watch' | 'safe'
  level_text: string
  advice: string
}

export function useBilling() {
  const loading = ref(false)
  const balance = ref(0)
  const bills = ref<Bill[]>([])
  const runway = ref<Runway | null>(null)
  const runwayLoading = ref(false)

  const pagination = reactive({
    page: 1,
    pageSize: 20,
    total: 0
  })

  /**
   * 加载余额
   */
  async function loadBalance() {
    try {
      const res: any = await api.get('/users/auth/me/')
      balance.value = res.balance || 0
    } catch (e) {
      console.error('加载余额失败:', e)
    }
  }

  /**
   * 加载账单列表
   */
  async function loadBills() {
    loading.value = true
    try {
      const res: any = await api.get('/users/billing/bills/', {
        params: {
          page: pagination.page,
          page_size: pagination.pageSize
        }
      })
      const data = res.data || res
      bills.value = data.results || []
      pagination.total = data.total || 0
    } catch (e) {
      console.error('加载账单失败:', e)
      bills.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * 加载余额续航预测
   */
  async function loadRunway() {
    runwayLoading.value = true
    try {
      const res: any = await api.get('/dashboard/user/balance-runway/')
      const data = res.data || res
      // 接口异常时给出空对象会被界面当成「有数据但全是 0」，这里明确置空
      runway.value = data && typeof data === 'object' && 'level' in data ? (data as Runway) : null
    } catch (e) {
      console.error('加载余额续航失败:', e)
      runway.value = null
    } finally {
      runwayLoading.value = false
    }
  }

  /**
   * 充值
   */
  async function recharge(amount: number) {
    const res = await api.post('/users/billing/recharge/', { amount })
    return res
  }

  /**
   * 卡密兑换
   */
  async function redeemCard(code: string) {
    const res: any = await api.post('/users/billing/redeem/', { code })
    return res
  }

  return {
    loading,
    balance,
    bills,
    runway,
    runwayLoading,
    pagination,
    loadBalance,
    loadBills,
    loadRunway,
    recharge,
    redeemCard
  }
}
