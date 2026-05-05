/**
 * 我的密钥 Composable
 */
import { ref, reactive } from 'vue'
import api from '@/stores'

export interface ApiKey {
  id: number
  name: string
  key: string
  rate_limit: number
  is_expired: boolean
  is_active: boolean
  created_at: string
  show?: boolean
}

export function useMyKeys() {
  const loading = ref(false)
  const keys = ref<ApiKey[]>([])

  /**
   * 加载密钥列表
   */
  async function loadKeys() {
    loading.value = true
    try {
      const res = await api.get('/users/keys/')
      keys.value = (res.results || res || []).map((k: ApiKey) => ({ ...k, show: false }))
    } catch (e) {
      console.error('加载密钥失败:', e)
      keys.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建密钥
   */
  async function createKey(data: {
    name: string
    rate_limit: number
    expires_at: string | null
    allow_ips: string
  }) {
    const res = await api.post('/users/keys/', {
      ...data,
      expires_at: data.expires_at ? new Date(data.expires_at).toISOString() : null
    })
    await loadKeys()
    return res
  }

  /**
   * 撤销密钥
   */
  async function revokeKey(id: number) {
    await api.delete(`/users/keys/${id}/`)
    await loadKeys()
  }

  return {
    loading,
    keys,
    loadKeys,
    createKey,
    revokeKey
  }
}
