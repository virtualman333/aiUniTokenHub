/**
 * 工单中心 Composable
 */
import { ref, reactive } from 'vue'
import api from '@/stores'

export interface TicketImage {
  id: number
  image: string
  url: string
  original_name: string
  file_size: number
  created_at: string
}

export interface Ticket {
  id: number
  title: string
  content?: string
  status: 'pending' | 'processing' | 'resolved'
  status_display: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  priority_display: string
  category: number | null
  category_name: string | null
  user: number
  username: string
  assigned_to?: number
  assigned_to_name?: string | null
  reply_count: number
  replies?: TicketReply[]
  images?: TicketImage[]
  resolved_at?: string | null
  created_at: string
  updated_at: string
}

export interface TicketReply {
  id: number
  ticket: number
  user: number
  username: string
  is_staff: boolean
  content: string
  is_staff_reply: boolean
  images?: TicketImage[]
  created_at: string
}

export interface TicketCategory {
  id: number
  name: string
  code: string
  description: string
  sort_order: number
  is_active: boolean
  created_at: string
}

export function useTickets() {
  const loading = ref(false)
  const tickets = ref<Ticket[]>([])
  const categories = ref<TicketCategory[]>([])

  const pagination = reactive({
    page: 1,
    pageSize: 20,
    total: 0
  })

  /**
   * 加载工单分类
   */
  async function loadCategories() {
    try {
      const res: any = await api.get('/tickets/categories/')
      categories.value = res.data || res || []
    } catch (e) {
      console.error('加载工单分类失败:', e)
    }
  }

  /**
   * 加载工单列表
   */
  async function loadTickets() {
    loading.value = true
    try {
      const res: any = await api.get('/tickets/', {
        params: {
          page: pagination.page,
          page_size: pagination.pageSize
        }
      })
      const data = res.data || res
      tickets.value = data.results || []
      pagination.total = data.total || 0
    } catch (e) {
      console.error('加载工单失败:', e)
      tickets.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取工单详情
   */
  async function getTicketDetail(id: number): Promise<Ticket | null> {
    try {
      const res: any = await api.get(`/tickets/${id}/`)
      return res.data || res
    } catch (e) {
      console.error('获取工单详情失败:', e)
      return null
    }
  }

  /**
   * 创建工单
   */
  async function createTicket(data: {
    title: string
    content: string
    category?: number
    priority?: string
    image_ids?: number[]
  }) {
    const res: any = await api.post('/tickets/', data)
    return res
  }

  /**
   * 回复工单
   */
  async function replyTicket(ticketId: number, content: string, imageIds?: number[]) {
    const res: any = await api.post(`/tickets/${ticketId}/reply/`, { content, image_ids: imageIds })
    return res
  }

  return {
    loading,
    tickets,
    categories,
    pagination,
    loadCategories,
    loadTickets,
    getTicketDetail,
    createTicket,
    replyTicket
  }
}
