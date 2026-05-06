/**
 * Chat Composable - 基于 OpenAI 兼容协议的 SSE 流式对话
 *
 * 后端入口：POST /api/proxy/v1/chat/completions
 * 鉴权：Authorization: Bearer <用户 APIKey, sk-...>
 *
 * 关键：
 * - 使用原生 fetch + ReadableStream 解析 SSE，避免 axios 的整段缓冲
 * - 内置"打字效果"队列：把收到的 token 入队，由 RAF/定时器按字 flush 到 UI
 *   即使后端一次性返回，也会呈现逐字打字效果
 */
import { ref } from 'vue'
import {
  appendMessage,
  type MessageItem,
} from './useConversations'

export interface ChatMessage {
  id?: number // 数据库 id（持久化后）
  role: 'system' | 'user' | 'assistant'
  content: string
  /** 仅前端使用：流式过程中标记是否还在生成 */
  pending?: boolean
  /** 仅前端使用：错误信息 */
  error?: string
  total_tokens?: number
  prompt_tokens?: number
  completion_tokens?: number
}

export interface SendOptions {
  apiKey: string
  model: string
  messages: Array<Pick<ChatMessage, 'role' | 'content'>>
  temperature?: number
  /** 流过程中：每次拿到上游推送的增量原始文本 */
  onDelta: (deltaText: string) => void
  /** 拿到 usage 信息时的回调 */
  onUsage?: (usage: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number }) => void
  /** 流结束回调，传完整原始文本 */
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
    onUsage,
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
        Accept: 'text/event-stream',
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
    let errMsg = `HTTP ${response.status}`
    try {
      const data = await response.json()
      errMsg = data?.error?.message || data?.detail || data?.msg || errMsg
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
            if (json.usage) onUsage?.(json.usage)
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
 * 字符打字队列：把收到的字符入队，按固定速率 flush 到 UI 文本
 * 这样即使上游一次性返回大段，UI 也会逐字展示。
 */
function createTypewriter(
  apply: (char: string) => void,
  options: { charsPerTick?: number; intervalMs?: number } = {}
) {
  const charsPerTick = options.charsPerTick ?? 2
  const intervalMs = options.intervalMs ?? 16
  let queue = ''
  let timer: number | null = null
  let finished = false
  let onIdle: (() => void) | null = null

  function start() {
    if (timer != null) return
    timer = window.setInterval(() => {
      if (queue.length === 0) {
        if (finished) {
          stop()
          onIdle?.()
        }
        return
      }
      const take = queue.slice(0, charsPerTick)
      queue = queue.slice(take.length)
      for (const ch of take) apply(ch)
    }, intervalMs)
  }

  function stop() {
    if (timer != null) {
      clearInterval(timer)
      timer = null
    }
  }

  function push(text: string) {
    queue += text
    start()
  }

  function finish(): Promise<void> {
    finished = true
    return new Promise((resolve) => {
      if (queue.length === 0) {
        stop()
        resolve()
      } else {
        onIdle = resolve
      }
    })
  }

  function flushAll() {
    if (queue.length > 0) {
      for (const ch of queue) apply(ch)
      queue = ''
    }
    stop()
  }

  return { push, finish, flushAll, stop }
}

/**
 * 顶层 composable：管理消息列表、发送状态、终止控制
 */
export function useChat() {
  const messages = ref<ChatMessage[]>([])
  const sending = ref(false)
  const conversationId = ref<number | null>(null)
  let abortCtrl: AbortController | null = null

  function loadFromMessages(remote: MessageItem[]) {
    messages.value = remote.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      total_tokens: m.total_tokens,
      prompt_tokens: m.prompt_tokens,
      completion_tokens: m.completion_tokens,
    }))
  }

  function reset() {
    messages.value = []
    conversationId.value = null
  }

  /**
   * 发送一条用户消息
   * 必须先有 conversationId（由调用方负责创建/选择会话）
   */
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
    if (!conversationId.value) throw new Error('未指定会话')
    if (sending.value) return

    // 第一次对话时，如果指定 systemPrompt 且历史中无 system，则注入并持久化
    if (
      systemPrompt &&
      systemPrompt.trim() &&
      !messages.value.some((m) => m.role === 'system')
    ) {
      const sysMsg: ChatMessage = { role: 'system', content: systemPrompt.trim() }
      messages.value.unshift(sysMsg)
      try {
        const saved = await appendMessage(conversationId.value, {
          role: 'system',
          content: sysMsg.content,
          model_code: model,
        })
        sysMsg.id = saved.id
      } catch {
        // 忽略持久化错误，仍可继续对话
      }
    }

    // 追加用户消息（持久化）
    const userMsg: ChatMessage = { role: 'user', content: userInput }
    messages.value.push(userMsg)
    try {
      const saved = await appendMessage(conversationId.value, {
        role: 'user',
        content: userMsg.content,
        model_code: model,
      })
      userMsg.id = saved.id
    } catch {
      // 忽略
    }

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

    // 字符打字机：把上游的 token 排队，逐字写入 assistantMsg.content
    const typer = createTypewriter((ch) => {
      assistantMsg.content += ch
    })

    let usage:
      | { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number }
      | undefined

    await streamChatCompletion({
      apiKey,
      model,
      messages: payloadMessages,
      temperature,
      signal: abortCtrl.signal,
      onDelta: (delta) => {
        typer.push(delta)
      },
      onUsage: (u) => {
        usage = u
      },
      onDone: async () => {
        await typer.finish()
        assistantMsg.pending = false
        if (usage) {
          assistantMsg.prompt_tokens = usage.prompt_tokens
          assistantMsg.completion_tokens = usage.completion_tokens
          assistantMsg.total_tokens = usage.total_tokens
        }
        sending.value = false

        // 持久化 assistant 消息
        if (conversationId.value && assistantMsg.content) {
          try {
            const saved = await appendMessage(conversationId.value, {
              role: 'assistant',
              content: assistantMsg.content,
              model_code: model,
              prompt_tokens: assistantMsg.prompt_tokens || 0,
              completion_tokens: assistantMsg.completion_tokens || 0,
              total_tokens: assistantMsg.total_tokens || 0,
            })
            assistantMsg.id = saved.id
          } catch {
            // ignore
          }
        }
      },
      onError: (msg) => {
        typer.flushAll()
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
    conversationId,
    send,
    abort,
    clear,
    reset,
    loadFromMessages,
  }
}
