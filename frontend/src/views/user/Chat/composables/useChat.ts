/**
 * Chat Composable - 基于 OpenAI 兼容协议的 SSE 流式对话
 *
 * 后端入口：POST /api/proxy/v1/chat/completions
 * 鉴权：Authorization: Bearer <用户 APIKey, sk-...>
 */
import { ref } from 'vue'

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
  /** 仅前端使用：流式过程中标记是否还在生成 */
  pending?: boolean
  /** 仅前端使用：错误信息 */
  error?: string
}

export interface SendOptions {
  apiKey: string
  model: string
  messages: Array<Pick<ChatMessage, 'role' | 'content'>>
  temperature?: number
  /** 用户消息追加到 messages 后的占位 assistant 消息 ref，便于实时刷新 UI */
  onDelta: (deltaText: string) => void
  /** 流结束回调，传完整文本 */
  onDone?: (fullText: string) => void
  /** 错误回调 */
  onError?: (msg: string) => void
  signal?: AbortSignal
}

/**
 * 调用后端 OpenAI 兼容接口，使用 SSE 流式读取，逐字回调
 */
export async function streamChatCompletion(opts: SendOptions): Promise<void> {
  const {
    apiKey,
    model,
    messages,
    temperature = 0.7,
    onDelta,
    onDone,
    onError,
    signal,
  } = opts

  const url = '/api/proxy/v1/chat/completions'

  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages,
        temperature,
        stream: true,
      }),
      signal,
    })
  } catch (e: any) {
    onError?.(e?.message || '网络请求失败')
    return
  }

  if (!response.ok || !response.body) {
    // 尝试解析错误体
    let errMsg = `HTTP ${response.status}`
    try {
      const data = await response.json()
      errMsg = data?.error?.message || data?.detail || errMsg
    } catch {
      // ignore
    }
    onError?.(errMsg)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let fullText = ''

  try {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // SSE 以 "\n\n" 分割事件
      let sepIndex: number
      // eslint-disable-next-line no-cond-assign
      while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.slice(0, sepIndex)
        buffer = buffer.slice(sepIndex + 2)

        // 每个事件可能由多行 "data: xxx" 组成（OpenAI 通常一行）
        const lines = rawEvent.split('\n')
        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data:')) continue
          const data = trimmed.slice(5).trim()
          if (!data) continue
          if (data === '[DONE]') {
            onDone?.(fullText)
            return
          }
          try {
            const json = JSON.parse(data)
            // 错误事件
            if (json.error) {
              const msg = json.error?.message || JSON.stringify(json.error)
              onError?.(msg)
              return
            }
            const delta: string =
              json?.choices?.[0]?.delta?.content ??
              json?.choices?.[0]?.message?.content ??
              ''
            if (delta) {
              fullText += delta
              onDelta(delta)
            }
          } catch {
            // 非 JSON 数据直接忽略
          }
        }
      }
    }
    onDone?.(fullText)
  } catch (e: any) {
    if (e?.name === 'AbortError') {
      onDone?.(fullText)
    } else {
      onError?.(e?.message || '流读取失败')
    }
  }
}

/**
 * 顶层 composable：管理消息列表、发送状态、终止控制
 */
export function useChat() {
  const messages = ref<ChatMessage[]>([])
  const sending = ref(false)
  let abortCtrl: AbortController | null = null

  async function send(params: {
    apiKey: string
    model: string
    userInput: string
    systemPrompt?: string
    temperature?: number
  }) {
    const { apiKey, model, userInput, systemPrompt, temperature } = params
    if (!apiKey) throw new Error('请选择一个 API 密钥')
    if (!model) throw new Error('请选择一个模型')
    if (!userInput.trim()) throw new Error('请输入内容')
    if (sending.value) return

    // 第一次对话时，如果指定 systemPrompt 且历史中无 system，则注入
    if (
      systemPrompt &&
      systemPrompt.trim() &&
      !messages.value.some((m) => m.role === 'system')
    ) {
      messages.value.unshift({ role: 'system', content: systemPrompt.trim() })
    }

    // 追加用户消息
    messages.value.push({ role: 'user', content: userInput })

    // 占位 assistant 消息
    const assistantMsg: ChatMessage = {
      role: 'assistant',
      content: '',
      pending: true,
    }
    messages.value.push(assistantMsg)

    sending.value = true
    abortCtrl = new AbortController()

    // 仅发送 role + content
    const payloadMessages = messages.value
      .filter((m) => m.role !== 'assistant' || !m.pending)
      .map((m) => ({ role: m.role, content: m.content }))

    await streamChatCompletion({
      apiKey,
      model,
      messages: payloadMessages,
      temperature,
      signal: abortCtrl.signal,
      onDelta: (delta) => {
        assistantMsg.content += delta
      },
      onDone: () => {
        assistantMsg.pending = false
        sending.value = false
      },
      onError: (msg) => {
        assistantMsg.error = msg
        assistantMsg.pending = false
        sending.value = false
      },
    })
  }

  function abort() {
    abortCtrl?.abort()
  }

  function clear() {
    messages.value = []
  }

  return {
    messages,
    sending,
    send,
    abort,
    clear,
  }
}
