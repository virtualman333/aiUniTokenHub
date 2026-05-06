/**
 * 会话相关 API（前端封装后端 /api/proxy/conversations）
 */
import api from '@/stores'

export interface ConversationItem {
  id: number
  title: string
  model_code: string
  system_prompt: string
  is_pinned: boolean
  last_message_at: string
  created_at: string
  last_message?: string
  message_count?: number
}

export interface MessageItem {
  id: number
  role: 'system' | 'user' | 'assistant'
  content: string
  model_code: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  usage_details?: Record<string, any>
  created_at: string
}

const BASE = '/proxy/conversations'

export async function listConversations(): Promise<ConversationItem[]> {
  const res: any = await api.get(`${BASE}/`)
  return Array.isArray(res) ? res : (res?.results || [])
}

export async function createConversation(payload: {
  title?: string
  model_code?: string
  system_prompt?: string
}): Promise<ConversationItem> {
  return await api.post(`${BASE}/`, payload)
}

export async function getConversationDetail(id: number): Promise<ConversationItem & { messages: MessageItem[] }> {
  return await api.get(`${BASE}/${id}/`)
}

export async function updateConversation(
  id: number,
  payload: Partial<Pick<ConversationItem, 'title' | 'is_pinned' | 'model_code' | 'system_prompt'>>
): Promise<ConversationItem> {
  return await api.patch(`${BASE}/${id}/`, payload)
}

export async function deleteConversation(id: number): Promise<void> {
  await api.delete(`${BASE}/${id}/`)
}

export async function clearConversation(id: number): Promise<void> {
  await api.post(`${BASE}/${id}/clear/`)
}

export async function appendMessage(
  conversationId: number,
  payload: {
    role: 'system' | 'user' | 'assistant'
    content: string
    model_code?: string
    prompt_tokens?: number
    completion_tokens?: number
    total_tokens?: number
    usage_details?: Record<string, any>
  }
): Promise<MessageItem> {
  return await api.post(`${BASE}/${conversationId}/messages/`, payload)
}

export async function deleteMessage(conversationId: number, messageId: number): Promise<void> {
  await api.delete(`${BASE}/${conversationId}/messages/${messageId}/`)
}
