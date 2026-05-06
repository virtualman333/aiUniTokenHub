<template>
  <div class="chat-page">
    <!-- 左：会话历史 -->
    <aside class="convo-pane">
      <div class="convo-head">
        <h3>对话历史</h3>
        <el-button type="primary" size="small" @click="handleNewConversation" :loading="creating">
          <el-icon><Plus /></el-icon>
          新建
        </el-button>
      </div>

      <div class="convo-list" v-loading="convoLoading">
        <div
          v-for="c in conversations"
          :key="c.id"
          class="convo-item"
          :class="{ active: c.id === currentConvoId }"
          @click="switchConversation(c.id)"
        >
          <div class="convo-icon">
            <el-icon><ChatLineRound /></el-icon>
          </div>
          <div class="convo-meta">
            <div class="convo-title">
              <el-icon v-if="c.is_pinned" class="pin"><Top /></el-icon>
              <span :title="c.title">{{ c.title }}</span>
            </div>
            <div class="convo-sub">{{ c.last_message || '暂无消息' }}</div>
          </div>
          <el-dropdown trigger="click" @click.stop>
            <span class="more">
              <el-icon><MoreFilled /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleRename(c)">
                  <el-icon><Edit /></el-icon> 重命名
                </el-dropdown-item>
                <el-dropdown-item @click="handlePin(c)">
                  <el-icon><Top /></el-icon>
                  {{ c.is_pinned ? '取消置顶' : '置顶' }}
                </el-dropdown-item>
                <el-dropdown-item @click="handleClear(c)">
                  <el-icon><Brush /></el-icon> 清空消息
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleDelete(c)">
                  <el-icon><Delete /></el-icon> 删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div v-if="!convoLoading && conversations.length === 0" class="convo-empty">
          暂无对话，点击右上角"新建"
        </div>
      </div>
    </aside>

    <!-- 右侧：聊天主区 -->
    <main class="chat-main">
      <!-- 顶部工具栏 -->
      <div class="toolbar">
        <div class="left">
          <el-select
            v-model="selectedModel"
            placeholder="选择模型"
            filterable
            :loading="modelsLoading"
            size="default"
            class="sel-model"
            @change="handleModelChange"
          >
            <el-option
              v-for="m in modelOptions"
              :key="m.code"
              :label="m.name"
              :value="m.code"
            >
              <div class="opt-row">
                <span>{{ m.name }}</span>
                <span class="opt-tag">{{ m.code }}</span>
              </div>
            </el-option>
          </el-select>

          <el-select
            v-model="selectedKeyId"
            placeholder="选择密钥"
            :loading="keysLoading"
            size="default"
            class="sel-key"
          >
            <el-option
              v-for="k in availableKeys"
              :key="k.id"
              :label="`${k.name} (${maskKey(k.key)})`"
              :value="k.id"
              :disabled="k.is_expired || !k.is_active"
            />
          </el-select>

          <el-popover placement="bottom" :width="280" trigger="click">
            <template #reference>
              <el-button>
                <el-icon><Setting /></el-icon> 参数
              </el-button>
            </template>
            <div class="param-pop">
              <div class="form-block">
                <label>系统提示（仅新会话生效）</label>
                <el-input
                  v-model="systemPrompt"
                  type="textarea"
                  :rows="3"
                  placeholder="例如：你是一个有用的助手"
                  :disabled="hasMessages"
                />
              </div>
              <div class="form-block">
                <label>Temperature {{ temperature.toFixed(2) }}</label>
                <el-slider
                  v-model="temperature"
                  :min="0"
                  :max="2"
                  :step="0.05"
                  :show-tooltip="false"
                />
              </div>
            </div>
          </el-popover>
        </div>
        <div class="right">
          <span class="hint">
            没密钥？
            <router-link to="/my-keys" class="link">前往创建</router-link>
          </span>
        </div>
      </div>

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
          :key="msg.id ?? idx"
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
            <template v-else>
              <!-- assistant 走 markdown，user 保持纯文本 -->
              <div
                v-if="msg.role === 'assistant'"
                class="md-content"
                v-html="renderMarkdown(msg.content) + (msg.pending ? cursorHtml : '')"
              />
              <div v-else class="msg-content user-content">
                {{ msg.content }}
              </div>
            </template>
            <div v-if="msg.role === 'assistant' && !msg.pending && msg.content" class="msg-actions">
              <el-button text size="small" @click="copyText(msg.content)">
                <el-icon><DocumentCopy /></el-icon> 复制
              </el-button>
              <el-popover
                v-if="msg.total_tokens"
                placement="top"
                trigger="hover"
                :width="240"
                popper-class="token-popover"
              >
                <template #reference>
                  <span class="token-hint">
                    <el-icon><DataLine /></el-icon>
                    tokens: {{ msg.total_tokens }}
                  </span>
                </template>
                <div class="token-detail">
                  <div class="td-title">Token 用量明细</div>
                  <div class="td-row">
                    <span>总计</span>
                    <strong>{{ msg.total_tokens || 0 }}</strong>
                  </div>
                  <div class="td-row">
                    <span>输入 (prompt)</span>
                    <strong>{{ msg.prompt_tokens || 0 }}</strong>
                  </div>
                  <div
                    v-if="getCachedTokens(msg) > 0"
                    class="td-row sub"
                  >
                    <span>└ 缓存命中</span>
                    <strong>{{ getCachedTokens(msg) }}</strong>
                  </div>
                  <div
                    v-if="getPromptAudio(msg) > 0"
                    class="td-row sub"
                  >
                    <span>└ 语音输入</span>
                    <strong>{{ getPromptAudio(msg) }}</strong>
                  </div>
                  <div class="td-row">
                    <span>输出 (completion)</span>
                    <strong>{{ msg.completion_tokens || 0 }}</strong>
                  </div>
                  <div
                    v-if="getReasoningTokens(msg) > 0"
                    class="td-row sub"
                  >
                    <span>└ 推理 (reasoning)</span>
                    <strong>{{ getReasoningTokens(msg) }}</strong>
                  </div>
                  <div
                    v-if="getAcceptedPrediction(msg) > 0"
                    class="td-row sub"
                  >
                    <span>└ 预测命中</span>
                    <strong>{{ getAcceptedPrediction(msg) }}</strong>
                  </div>
                  <div
                    v-if="getRejectedPrediction(msg) > 0"
                    class="td-row sub"
                  >
                    <span>└ 预测拒绝</span>
                    <strong>{{ getRejectedPrediction(msg) }}</strong>
                  </div>
                  <div
                    v-if="getCacheCreation(msg) > 0"
                    class="td-row sub"
                  >
                    <span>└ 缓存创建 (Anthropic)</span>
                    <strong>{{ getCacheCreation(msg) }}</strong>
                  </div>
                  <div
                    v-if="getCacheRead(msg) > 0"
                    class="td-row sub"
                  >
                    <span>└ 缓存读取 (Anthropic)</span>
                    <strong>{{ getCacheRead(msg) }}</strong>
                  </div>
                </div>
              </el-popover>
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
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Setting,
  Delete,
  ChatRound,
  ChatLineRound,
  User,
  Cpu,
  Promotion,
  CircleClose,
  WarningFilled,
  Plus,
  MoreFilled,
  Edit,
  Top,
  Brush,
  DocumentCopy,
  DataLine,
} from '@element-plus/icons-vue'
import { useChat } from './composables/useChat'
import { useMyKeys } from '../MyKeys/composables/useMyKeys'
import { useModels } from '../ModelSquare/composables/useModels'
import {
  listConversations,
  createConversation,
  getConversationDetail,
  updateConversation,
  deleteConversation,
  clearConversation,
  type ConversationItem,
} from './composables/useConversations'
import { renderMarkdown } from '@/utils/markdown'

const route = useRoute()
const router = useRouter()

const {
  messages,
  sending,
  conversationId,
  send,
  abort,
  loadFromMessages,
  reset,
} = useChat()
const { keys, loading: keysLoading, loadKeys } = useMyKeys()
const { models, loading: modelsLoading, fetchModels } = useModels()

const conversations = ref<ConversationItem[]>([])
const convoLoading = ref(false)
const creating = ref(false)
const currentConvoId = computed(() => conversationId.value)

const selectedKeyId = ref<number | null>(null)
const selectedModel = ref<string>('')
const systemPrompt = ref<string>('')
const temperature = ref<number>(0.7)
const inputText = ref<string>('')
const messagesRef = ref<HTMLElement | null>(null)

const cursorHtml = '<span class="typing-cursor">▍</span>'

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
  await Promise.all([loadKeys(), fetchModels(), loadConversations()])
  // 默认选第一个可用密钥
  const firstUsable = keys.value.find((k) => !k.is_expired && k.is_active)
  if (firstUsable) selectedKeyId.value = firstUsable.id

  // URL 上的 ?model=xxx 优先级最高
  const queryModel = (route.query.model as string | undefined) || ''

  // 默认选择第一个会话；没有则创建
  if (conversations.value.length > 0) {
    await switchConversation(conversations.value[0].id)
  } else {
    await handleNewConversation()
  }

  // switchConversation/handleNewConversation 会把 selectedModel 设为会话保存的 model_code，
  // 这里如果 URL 上带了 model，就用它覆盖（并同步到当前会话）。
  if (queryModel) {
    applyModelFromQuery(queryModel)
  } else if (!selectedModel.value && modelOptions.value.length > 0) {
    selectedModel.value = modelOptions.value[0].code
  }
})

watch(
  messages,
  () => {
    scrollToBottom()
  },
  { deep: true }
)

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
  if (e.shiftKey) return
  e.preventDefault()
  handleSend()
}

async function handleSend() {
  if (!canSend.value) return
  if (!conversationId.value) {
    await handleNewConversation()
  }
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
    // 刷新会话列表（更新 last_message_at / 标题）
    loadConversations()
  } catch (e: any) {
    ElMessage.error(e?.message || '发送失败')
  }
}

function handleAbort() {
  abort()
}

function handleModelChange() {
  // 把模型记录到当前会话
  if (conversationId.value) {
    updateConversation(conversationId.value, { model_code: selectedModel.value }).catch(() => {})
  }
}

// ============== 会话操作 ==============

async function loadConversations() {
  convoLoading.value = true
  try {
    conversations.value = await listConversations()
  } catch (e) {
    console.error('加载会话失败', e)
  } finally {
    convoLoading.value = false
  }
}

async function handleNewConversation() {
  creating.value = true
  try {
    const c = await createConversation({
      title: '新对话',
      model_code: selectedModel.value || '',
      system_prompt: systemPrompt.value || '',
    })
    conversations.value.unshift(c)
    conversationId.value = c.id
    reset()
    conversationId.value = c.id
    if (c.system_prompt) systemPrompt.value = c.system_prompt
  } catch (e: any) {
    ElMessage.error(e?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

async function switchConversation(id: number) {
  if (sending.value) {
    ElMessage.warning('正在生成中，请先停止')
    return
  }
  try {
    const detail = await getConversationDetail(id)
    conversationId.value = id
    selectedModel.value = detail.model_code || selectedModel.value
    systemPrompt.value = detail.system_prompt || ''
    loadFromMessages(detail.messages || [])
  } catch (e: any) {
    ElMessage.error(e?.message || '加载会话失败')
  }
}

async function handleRename(c: ConversationItem) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新标题', '重命名', {
      inputValue: c.title,
      inputPattern: /.+/,
      inputErrorMessage: '标题不能为空',
    })
    const updated = await updateConversation(c.id, { title: value })
    Object.assign(c, updated)
  } catch {
    // 取消
  }
}

async function handlePin(c: ConversationItem) {
  const updated = await updateConversation(c.id, { is_pinned: !c.is_pinned })
  Object.assign(c, updated)
  // 重新排序
  loadConversations()
}

async function handleClear(c: ConversationItem) {
  try {
    await ElMessageBox.confirm(`确定清空"${c.title}"的所有消息？`, '提示', {
      type: 'warning',
    })
    await clearConversation(c.id)
    if (conversationId.value === c.id) {
      reset()
      conversationId.value = c.id
    }
    ElMessage.success('已清空')
    loadConversations()
  } catch {
    // 取消
  }
}

async function handleDelete(c: ConversationItem) {
  try {
    await ElMessageBox.confirm(`确定删除"${c.title}"？该操作不可恢复`, '提示', {
      type: 'warning',
    })
    await deleteConversation(c.id)
    conversations.value = conversations.value.filter((x) => x.id !== c.id)
    if (conversationId.value === c.id) {
      // 切到下一个会话或新建
      if (conversations.value.length > 0) {
        await switchConversation(conversations.value[0].id)
      } else {
        reset()
        await handleNewConversation()
      }
    }
    ElMessage.success('已删除')
  } catch {
    // 取消
  }
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

// ============== Token 明细辅助 ==============
function getCachedTokens(msg: any): number {
  return Number(msg?.usage?.prompt_tokens_details?.cached_tokens || 0)
}
function getPromptAudio(msg: any): number {
  return Number(msg?.usage?.prompt_tokens_details?.audio_tokens || 0)
}
function getReasoningTokens(msg: any): number {
  return Number(msg?.usage?.completion_tokens_details?.reasoning_tokens || 0)
}
function getAcceptedPrediction(msg: any): number {
  return Number(msg?.usage?.completion_tokens_details?.accepted_prediction_tokens || 0)
}
function getRejectedPrediction(msg: any): number {
  return Number(msg?.usage?.completion_tokens_details?.rejected_prediction_tokens || 0)
}
function getCacheCreation(msg: any): number {
  return Number(msg?.usage?.cache_creation_input_tokens || 0)
}
function getCacheRead(msg: any): number {
  return Number(msg?.usage?.cache_read_input_tokens || 0)
}

// 路由 query 改变时（如从模型广场再次跳转）切换模型
watch(
  () => route.query.model,
  (val) => {
    if (val && typeof val === 'string') {
      applyModelFromQuery(val)
    }
  }
)

/**
 * 将 URL ?model=xxx 应用到当前选择，并同步到当前会话
 * - 若该模型存在于模型列表，则选中
 * - 若不存在，仍然写入（用户可能用的是仅 code 已知的模型）
 * - 同步到当前会话的 model_code
 */
function applyModelFromQuery(code: string) {
  if (!code) return
  if (selectedModel.value === code) return
  selectedModel.value = code
  handleModelChange()
}
</script>

<style scoped>
.chat-page {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  height: calc(100vh - 64px - 48px);
  min-height: 560px;
}

/* ============= 会话历史 ============= */
.convo-pane {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.convo-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
}

.convo-head h3 {
  margin: 0;
  font-size: 15px;
  color: #111827;
  font-weight: 600;
}

.convo-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}

.convo-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.convo-item:hover {
  background: #f3f4f6;
}

.convo-item.active {
  background: #ecfdf5;
}

.convo-item.active .convo-title span {
  color: #047857;
}

.convo-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #ecfdf5;
  color: #059669;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.convo-meta {
  flex: 1;
  min-width: 0;
}

.convo-title {
  font-size: 13px;
  font-weight: 500;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 4px;
  overflow: hidden;
}

.convo-title span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.convo-title .pin {
  color: #f59e0b;
  font-size: 12px;
}

.convo-sub {
  font-size: 12px;
  color: #9ca3af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
}

.convo-empty {
  text-align: center;
  color: #9ca3af;
  padding: 32px 12px;
  font-size: 13px;
}

.more {
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.more:hover {
  background: #fff;
  color: #374151;
}

/* ============= 聊天主区 ============= */
.chat-main {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}

.toolbar {
  padding: 10px 14px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar .left {
  display: flex;
  gap: 8px;
  align-items: center;
}

.sel-model {
  width: 220px;
}

.sel-key {
  width: 220px;
}

.toolbar .hint {
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

.param-pop .form-block {
  margin-bottom: 12px;
}

.param-pop label {
  display: block;
  font-size: 12px;
  color: #4b5563;
  margin-bottom: 6px;
}

/* 消息区 */
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
  max-width: 78%;
  padding: 12px 16px;
  border-radius: 12px;
  background: #f3f4f6;
  color: #1f2937;
  line-height: 1.7;
  font-size: 14px;
  word-break: break-word;
}

.msg-row.user .msg-bubble {
  background: #059669;
  color: #fff;
  border-bottom-right-radius: 4px;
  white-space: pre-wrap;
}

.msg-row.user .user-content {
  white-space: pre-wrap;
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

.msg-actions {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #e5e7eb;
  display: flex;
  align-items: center;
  gap: 8px;
}

.token-hint {
  font-size: 12px;
  color: #9ca3af;
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: help;
  transition: background 0.15s, color 0.15s;
}

.token-hint:hover {
  background: #f3f4f6;
  color: #4b5563;
}

.token-detail {
  font-size: 13px;
  color: #1f2937;
}

.token-detail .td-title {
  font-weight: 600;
  font-size: 13px;
  color: #111827;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f1f5f9;
}

.token-detail .td-row {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  font-size: 12px;
}

.token-detail .td-row strong {
  color: #059669;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.token-detail .td-row.sub {
  color: #6b7280;
  padding-left: 8px;
}

.token-detail .td-row.sub strong {
  color: #6b7280;
  font-weight: 500;
}

/* ============= Markdown 内容样式 ============= */
.md-content :deep(p) {
  margin: 0 0 8px;
}
.md-content :deep(p:last-child) {
  margin-bottom: 0;
}
.md-content :deep(h1),
.md-content :deep(h2),
.md-content :deep(h3),
.md-content :deep(h4) {
  margin: 12px 0 6px;
  font-weight: 600;
}
.md-content :deep(h1) { font-size: 20px; }
.md-content :deep(h2) { font-size: 18px; }
.md-content :deep(h3) { font-size: 16px; }
.md-content :deep(ul),
.md-content :deep(ol) {
  margin: 6px 0;
  padding-left: 22px;
}
.md-content :deep(li) {
  margin: 2px 0;
}
.md-content :deep(blockquote) {
  border-left: 3px solid #d1d5db;
  margin: 6px 0;
  padding: 4px 12px;
  color: #6b7280;
  background: #f9fafb;
}
.md-content :deep(code) {
  background: #f3f4f6;
  color: #db2777;
  padding: 2px 5px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
}
.md-content :deep(pre) {
  background: #0d1117;
  color: #e6edf3;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}
.md-content :deep(pre code) {
  background: transparent !important;
  color: inherit;
  padding: 0;
  font-size: 13px;
}
.md-content :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  width: 100%;
}
.md-content :deep(th),
.md-content :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 6px 10px;
  text-align: left;
}
.md-content :deep(th) {
  background: #f9fafb;
}
.md-content :deep(a) {
  color: #2563eb;
  text-decoration: none;
}
.md-content :deep(a:hover) {
  text-decoration: underline;
}
.md-content :deep(.typing-cursor) {
  display: inline-block;
  margin-left: 1px;
  color: #10b981;
  font-weight: bold;
  animation: blink 1s infinite;
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
  .convo-pane {
    max-height: 280px;
  }
}
</style>
