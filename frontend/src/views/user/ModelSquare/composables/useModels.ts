/**
 * 模型广场 Composable
 * 封装模型列表相关的状态和逻辑
 */
import { ref } from 'vue'
import axios from 'axios'

// 创建独立的 axios 实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 筛选条件类型
export interface Filters {
  providers: Array<{ code: string; name: string }>
  categories: Array<{ code: string; name: string }>
  capabilities: Array<{ code: string; name: string }>
  pricing_types: string[]
}

// 模型类型
export interface AIModel {
  id: number
  name: string
  code: string
  provider_name: string
  provider_logo?: string
  category_name?: string
  description?: string
  input_price: number
  output_price: number
  context_window: number
  max_tokens: number
  supports_streaming: boolean
  supports_vision: boolean
  supports_tools: boolean
  supports_json: boolean
  status: string
  is_featured: boolean
  is_new: boolean
  usage_count: number
  rating: number
  tags: string[]
}

export function useModels() {
  const loading = ref(false)
  const models = ref<AIModel[]>([])
  const filters = ref<Filters>({
    providers: [],
    categories: [],
    capabilities: [],
    pricing_types: []
  })

  // 搜索防抖
  let searchTimer: ReturnType<typeof setTimeout> | null = null

  /**
   * 获取筛选条件
   */
  async function fetchFilters() {
    try {
      const res = await api.get('/models/models/filters/')
      filters.value = res
    } catch (e) {
      console.error('获取筛选条件失败:', e)
    }
  }

  /**
   * 获取模型列表
   */
  async function fetchModels(params: Record<string, string> = {}) {
    loading.value = true
    try {
      const res = await api.get('/models/models/', { params })
      models.value = res
    } catch (e) {
      console.error('获取模型列表失败:', e)
    } finally {
      loading.value = false
    }
  }

  /**
   * 防抖搜索
   */
  function debounceSearch(callback: () => void, delay = 300) {
    if (searchTimer) clearTimeout(searchTimer)
    searchTimer = setTimeout(callback, delay)
  }

  /**
   * 格式化价格
   */
  function formatPrice(price: number | string | null): string {
    if (!price || price == 0) return '0.00'
    return parseFloat(String(price)).toFixed(6)
  }

  /**
   * 格式化数字
   */
  function formatNumber(num: number | string | null): string {
    if (!num) return '0'
    const n = Number(num)
    if (n >= 10000) {
      return (n / 10000).toFixed(1) + 'w'
    }
    return String(n)
  }

  return {
    loading,
    models,
    filters,
    fetchFilters,
    fetchModels,
    debounceSearch,
    formatPrice,
    formatNumber
  }
}
