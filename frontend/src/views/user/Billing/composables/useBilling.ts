/**
 * 账单中心 Composable
 */
import { ref, reactive } from 'vue'
import api from '@/stores'

export interface Bill {
  id: number
  type: 'recharge' | 'consume' | 'refund'
  amount: number
  balance: number
  description: string
  created_at: string
}

export function useBilling() {
  const loading = ref(false)
  const balance = ref(0)
  const bills = ref<Bill[]>([])

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
      const res = await api.get('/users/auth/me/')
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
      const res: any = await api.get('/users/bills/', {
        params: {
          page: pagination.page,
          page_size: pagination.pageSize
        }
      })
      bills.value = res.results || res || []
      pagination.total = res.total || bills.value.length
    } catch (e) {
      console.error('加载账单失败:', e)
      bills.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * 充值
   */
  async function recharge(amount: number) {
    const res = await api.post('/users/recharge/', { amount })
    // 打开支付链接或处理支付
    return res
  }

  return {
    loading,
    balance,
    bills,
    pagination,
    loadBalance,
    loadBills,
    recharge
  }
}
