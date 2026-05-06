<template>
  <div class="chat-page">
    <!-- 左侧侧边栏：模型 / 密钥 / 参数 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>AI 对话</h2>
        <p class="subtitle">基于 OpenAI 协议 · SSE 流式输出</p>
      </div>

      <div class="form-block">
        <label class="form-label">
          <el-icon><Box /></el-icon>
          选择模型
        </label>
        <el-select
          v-model="selectedModel"
          placeholder="请选择模型"
          filterable
          :loading="modelsLoading"
          class="full"
        >
          <el-option
            v-for="m in modelOptions"
            :key="m.code"
            :label="m.label"
            :value="m.code"
          >
            <div class="opt-row">
              <span>{{ m.name }}</span>
              <span class="opt-tag">{{ m.code }}</span>
            </div>
          </el-option>
        </el-select>
      </div>

      <div class="form-block">
        <label class="form-label">
          <el-icon><Key /></el-icon>
          选择密钥
        </label>
        <el-select
          v-model="selectedKeyId"
          placeholder="请选择 API 密钥"
          :loading="keysLoading"
          class="full"
        >
          <el-option
            v-for="k in availableKeys"
            :key="k.id"
            :label="`${k.name} (${maskKey(k.key)})`"
            :value="k.id"
            :disabled="k.is_expired || !k.is_active"
          />
        </el-select>
        <div class="hint">
          没有密钥？
          <router-link to="/my-keys" class="link">前往创建</router-link>
        </div>
      </div>

      <div class="form-block">
        <label class="form-label">
          <el-icon><Setting /></el-icon>
          系统提示（可选）
        </label>
        <el-input
          v-model="systemPrompt"
          type="textarea"
          :rows="3"
          placeholder="例如：你是一个有用的助手"
          :disabled="hasMessages"
        />
      </div>

      <div class="form-block">
        <label class="form-label">温度 (Temperature) {{ temperature.toFixed(2) }}</label>
        <el-slider
          v-model="temperature"
          :min="0"
          :max="2"
          :step="0.05"
          :show-tooltip="false"
        />
      </div>

      <div class="form-actions">
        <el-button :disabled="!hasMessages || sending" @click="handleClear">
          <el-icon><Delete /></el-icon>
          清空对话
        </el-button>
      </div>
    </aside>

    <!-- 右侧聊天主区 -->
    <main class="chat-main">
      <!-- 消息列表 -->
      <div class="messages" ref="messagesRef">
        <div v-if="visibleMessages.length === 0" class="empty">
          <div class="empty-icon">
            <el-icon :size="56"><ChatRound /></el-icon>
          </div>
          <h3>开始一场新的对话</h3>
          <p>选择模型与密钥后，在下方输入消息</p>
        </div>

        <div
          v-for="(msg, idx) in visibleMessages"
          :key="idx"
          class="msg-row"
          :class="msg.role"
        >
          <div class="avatar" :class="msg.role">
            <el-icon v-if="msg.role === 'user'"><User /></el-icon>
            <el-icon v-else><Cpu /></el-icon>
          </div>
          <div class="msg-bubble" :class="{ 'has-error': !!msg.error }">
            <div v-if="msg.error" class="msg-error">
              <el-icon><WarningFilled /></el-icon>
              <span>{{ msg.error }}</span>
            </div>
            <div v-else class="msg-content">
              <span>{{ msg.content }}</span>
              <span v-if="msg.pending" class="cursor">▍</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="input-area">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="3"
          resize="none"
          placeholder="输入消息（Enter 发送 / Shift+Enter 换行）"
          @keydown.enter="handleEnter"
          :disabled="sending"
        />
        <div class="input-actions">
          <span class="meta">
            <template v-if="selectedModel">模型：{{ selectedModel }}</template>
          </span>
          <div class="actions">
            <el-button v-if="sending" type="warning" @click="handleAbort">
              <el-icon><CircleClose /></el-icon> 停止
            </el-button>
            <el-button
              type="primary"
              :loading="sending"
              :disabled="!canSend"
              @click="handleSend"
            >
              <el-icon><Promotion /></el-icon>
              发送
            </el-button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Box,
  Key,
  Setting,
  Delete,
  ChatRound,
  User,
  Cpu,
  Promotion,
  CircleClose,
  WarningFilled,
} from '@element-plus/icons-vue'
import { useChat } from './composables/useChat'
import { useMyKeys } from '../MyKeys/composables/useMyKeys'
import { useModels } from '../ModelSquare/composables/useModels'

const { messages, sending, send, abort, clear } = useChat()
const { keys, loading: keysLoading, loadKeys } = useMyKeys()
const { models, loading: modelsLoading, fetchModels } = useModels()

const selectedKeyId = ref<number | null>(null)
const selectedModel = ref<string>('')
const systemPrompt = ref<string>('')
const temperature = ref<number>(0.7)
const inputText = ref<string>('')
const messagesRef = ref<HTMLElement | null>(null)

// 仅展示非 system 消息
const visibleMessages = computed(() =>
  messages.value.filter((m) => m.role !== 'system')
)
const hasMessages = computed(() => messages.value.length > 0)

const availableKeys = computed(() => keys.value)

const modelOptions = computed(() =>
  (models.value || []).map((m: any) => ({
    code: m.code,
    name: m.name,
    label: `${m.name} · ${m.code}`,
  }))
)

const selectedKey = computed(
  () => availableKeys.value.find((k) => k.id === selectedKeyId.value) || null
)

const canSend = computed(
  () =>
    !!inputText.value.trim() &&
    !!selectedModel.value &&
    !!selectedKey.value &&
    !sending.value
)

onMounted(async () => {
  await Promise.all([loadKeys(), fetchModels()])
  // 默认选第一个可用密钥
  const firstUsable = keys.value.find((k) => !k.is_expired && k.is_active)
  if (firstUsable) selectedKeyId.value = firstUsable.id
  // 默认选第一个模型
  if (modelOptions.value.length > 0) selectedModel.value = modelOptions.value[0].code
})

watch(messages, () => {
  scrollToBottom()
}, { deep: true })

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

function maskKey(key: string) {
  if (!key) return ''
  return key.substring(0, 6) + '...' + key.substring(key.length - 4)
}

function handleEnter(e: KeyboardEvent) {
  if (e.shiftKey) return // 允许 shift+enter 换行
  e.preventDefault()
  handleSend()
}

async function handleSend() {
  if (!canSend.value) return
  const text = inputText.value
  inputText.value = ''
  try {
    await send({
      apiKey: selectedKey.value!.key,
      model: selectedModel.value,
      userInput: text,
      systemPrompt: systemPrompt.value,
      temperature: temperature.value,
    })
  } catch (e: any) {
    ElMessage.error(e?.message || '发送失败')
  }
}

function handleAbort() {
  abort()
}

function handleClear() {
  clear()
}
</script>

<style scoped>
.chat-page {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  height: calc(100vh - 64px - 48px);
  min-height: 560px;
}

/* ============= 侧边栏 ============= */
.sidebar {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow-y: auto;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1f2937;
  font-weight: 600;
}

.sidebar-header .subtitle {
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
}

.form-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #374151;
  font-weight: 500;
}

.full {
  width: 100%;
}

.opt-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.opt-tag {
  font-size: 12px;
  color: #9ca3af;
  font-family: monospace;
}

.hint {
  font-size: 12px;
  color: #6b7280;
}

.link {
  color: #059669;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.form-actions {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px dashed #e5e7eb;
}

/* ============= 主聊天区 ============= */
.chat-main {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: linear-gradient(180deg, #f9fafb 0%, #fff 100%);
}

.empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
}

.empty-icon {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: #ecfdf5;
  color: #10b981;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.empty h3 {
  margin: 0 0 4px;
  color: #374151;
  font-weight: 600;
}

.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: flex-start;
}

.msg-row.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
  font-size: 18px;
}

.avatar.user {
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.avatar.assistant {
  background: linear-gradient(135deg, #10b981, #059669);
}

.msg-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  background: #f3f4f6;
  color: #1f2937;
  line-height: 1.6;
  font-size: 14px;
  word-break: break-word;
  white-space: pre-wrap;
}

.msg-row.user .msg-bubble {
  background: #059669;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.msg-row.assistant .msg-bubble {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-bottom-left-radius: 4px;
}

.msg-bubble.has-error {
  background: #fef2f2 !important;
  border-color: #fecaca !important;
  color: #b91c1c !important;
}

.msg-error {
  display: flex;
  align-items: center;
  gap: 6px;
}

.msg-content .cursor {
  display: inline-block;
  margin-left: 2px;
  animation: blink 1s infinite;
  color: #10b981;
  font-weight: bold;
}

@keyframes blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

/* ============= 输入区 ============= */
.input-area {
  border-top: 1px solid #e5e7eb;
  padding: 14px 18px 16px;
  background: #fff;
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.input-actions .meta {
  font-size: 12px;
  color: #9ca3af;
}

.input-actions .actions {
  display: flex;
  gap: 8px;
}

@media (max-width: 900px) {
  .chat-page {
    grid-template-columns: 1fr;
    height: auto;
  }

  .sidebar {
    order: 2;
  }
}
</style>
