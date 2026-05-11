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
              <el-icon v-if="c.is_pinned" class="pin"><ArrowUp /></el-icon>
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
                  <el-icon><ArrowUp /></el-icon>
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

        <MessageBubble
          v-for="(msg, idx) in visibleMessages"
          :key="msg.id ?? idx"
          :msg="msg"
          @copy="copyText"
        />
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
  Promotion,
  CircleClose,
  Plus,
  MoreFilled,
  Edit,
  ArrowUp,
  Brush,
} from '@element-plus/icons-vue'
import api from '@/stores'
import { useChat } from './composables/useChat'
import { useMyKeys } from '../MyKeys/composables/useMyKeys'
import { useModels } from '../ModelSquare/composables/useModels'
import MessageBubble from './components/MessageBubble.vue'
import {
  listConversations,
  createConversation,
  getConversationDetail,
  updateConversation,
  deleteConversation,
  clearConversation,
  type ConversationItem,
} from './composables/useConversations'
import { copyToClipboard } from '@/utils/clipboard'

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

// 仅展示非 system 消息
const visibleMessages = computed(() =>
  messages.value.filter((m) => m.role !== 'system')
)
const hasMessages = computed(() => messages.value.length > 0)

const availableKeys = computed(() => keys.value)

// 拉取全部模型（不限制 page_size），用于下拉选择
const chatModels = ref<any[]>([])

const modelOptions = computed(() =>
  (chatModels.value || models.value || []).map((m: any) => ({
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

async function fetchAllModels() {
  try {
    const res: any = await api.get('/models/models/', { params: { page: '1', page_size: '9999', category: 'llm' } })
    chatModels.value = res.results || res || []
  } catch (e) {
    // 降级：使用共享的 fetchModels（默认 20 条）
    await fetchModels()
  }
}

onMounted(async () => {
  await Promise.all([loadKeys(), fetchAllModels(), loadConversations()])
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

// 流式时高频更新，对最后一条消息的内容做轻量 watch（不开 deep）
let scrollPending = false
watch(
  () => visibleMessages.value.length + ':' + (visibleMessages.value[visibleMessages.value.length - 1]?.content?.length || 0),
  () => {
    if (scrollPending) return
    scrollPending = true
    requestAnimationFrame(() => {
      scrollPending = false
      if (messagesRef.value) {
        messagesRef.value.scrollTop = messagesRef.value.scrollHeight
      }
    })
  }
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
  const success = await copyToClipboard(text)
  if (success) {
    ElMessage.success('已复制')
  } else {
    ElMessage.error('复制失败')
  }
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
  grid-template-columns: 300px 1fr;
  gap: var(--space-4);
  height: calc(100vh - var(--header-height) - var(--space-12));
  min-height: 600px;
  animation: fadeIn 0.5s ease-out;
  min-width: 0;
}

/* ============= 会话历史 ============= */
.convo-pane {
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.convo-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-light);
  background: var(--neutral-50);
}

.convo-head h3 {
  margin: 0;
  font-size: var(--text-base);
  color: var(--text-primary);
  font-weight: var(--font-semibold);
}

.convo-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}

.convo-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: var(--space-1);
  
  &:hover {
    background: var(--neutral-50);
  }
  
  &.active {
    background: var(--primary-50);
    border: 1px solid var(--primary-100);
    
    .convo-title span {
      color: var(--primary-700);
    }
    
    .convo-icon {
      background: var(--primary-100);
      color: var(--primary-600);
    }
  }
}

.convo-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--success-50);
  color: var(--success-600);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-fast);
}

.convo-meta {
  flex: 1;
  min-width: 0;
}

.convo-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: var(--space-1);
  overflow: hidden;
}

.convo-title span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.convo-title .pin {
  color: var(--warning-500);
  font-size: var(--text-xs);
}

.convo-sub {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: var(--space-1);
}

.convo-empty {
  text-align: center;
  color: var(--text-tertiary);
  padding: var(--space-8) var(--space-3);
  font-size: var(--text-sm);
}

.more {
  color: var(--text-tertiary);
  cursor: pointer;
  padding: var(--space-1);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  
  &:hover {
    background: var(--bg-primary);
    color: var(--text-secondary);
  }
}

/* ============= 聊天主区 ============= */
.chat-main {
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  min-width: 0;
}

.toolbar {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  background: var(--neutral-50);
}

.toolbar .left {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  min-width: 0;
}

.sel-model {
  width: 240px;
}

.sel-key {
  width: 240px;
}

.toolbar .hint {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.link {
  color: var(--primary-600);
  text-decoration: none;
  font-weight: var(--font-medium);
  
  &:hover {
    text-decoration: underline;
  }
}

.opt-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
}

.opt-tag {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.param-pop .form-block {
  margin-bottom: var(--space-3);
}

.param-pop label {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
  font-weight: var(--font-medium);
}

/* 消息区 */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
  background: linear-gradient(180deg, var(--neutral-50) 0%, var(--bg-primary) 100%);
}

.empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
}

.empty-icon {
  width: 120px;
  height: 120px;
  border-radius: var(--radius-full);
  background: var(--primary-50);
  color: var(--primary-500);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-6);
  box-shadow: var(--shadow-lg);
}

.empty h3 {
  margin: 0 0 var(--space-2);
  color: var(--text-primary);
  font-weight: var(--font-semibold);
  font-size: var(--text-xl);
}

.msg-row {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
  align-items: flex-start;
  
  &.user {
    flex-direction: row-reverse;
  }
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--text-inverse);
  font-size: var(--text-lg);
  box-shadow: var(--shadow-sm);
  
  &.user {
    background: var(--gradient-primary);
  }
  
  &.assistant {
    background: var(--gradient-success);
  }
}

.msg-bubble {
  max-width: 78%;
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-xl);
  background: var(--neutral-100);
  color: var(--text-primary);
  line-height: var(--leading-relaxed);
  font-size: var(--text-sm);
  word-break: break-word;
  box-shadow: var(--shadow-xs);
  
  &.has-error {
    background: var(--error-50) !important;
    border-color: var(--error-200) !important;
    color: var(--error-800) !important;
  }
}

.msg-row.user .msg-bubble {
  background: var(--gradient-primary);
  color: var(--text-inverse);
  border-bottom-right-radius: var(--radius-sm);
  white-space: pre-wrap;
}

.msg-row.user .user-content {
  white-space: pre-wrap;
}

.msg-row.assistant .msg-bubble {
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  border-bottom-left-radius: var(--radius-sm);
}

.msg-error {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.msg-actions {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px dashed var(--border-light);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.token-hint {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  cursor: help;
  transition: all var(--transition-fast);
  
  &:hover {
    background: var(--neutral-100);
    color: var(--text-secondary);
  }
}

.token-detail {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.token-detail .td-title {
  font-weight: var(--font-semibold);
  font-size: var(--text-sm);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-light);
}

.token-detail .td-row {
  display: flex;
  justify-content: space-between;
  padding: var(--space-1) 0;
  font-size: var(--text-xs);
  
  strong {
    color: var(--success-600);
    font-weight: var(--font-semibold);
    font-variant-numeric: tabular-nums;
  }
  
  &.sub {
    color: var(--text-tertiary);
    padding-left: var(--space-2);
    
    strong {
      color: var(--text-tertiary);
      font-weight: var(--font-medium);
    }
  }
}

/* ============= Markdown 内容样式 ============= */
.md-content :deep(p) {
  margin: 0 0 var(--space-2);
  
  &:last-child {
    margin-bottom: 0;
  }
}

.md-content :deep(h1),
.md-content :deep(h2),
.md-content :deep(h3),
.md-content :deep(h4) {
  margin: var(--space-3) 0 var(--space-2);
  font-weight: var(--font-semibold);
}

.md-content :deep(h1) { font-size: var(--text-xl); }
.md-content :deep(h2) { font-size: var(--text-lg); }
.md-content :deep(h3) { font-size: var(--text-base); }

.md-content :deep(ul),
.md-content :deep(ol) {
  margin: var(--space-2) 0;
  padding-left: var(--space-6);
}

.md-content :deep(li) {
  margin: var(--space-1) 0;
}

.md-content :deep(blockquote) {
  border-left: 3px solid var(--neutral-300);
  margin: var(--space-2) 0;
  padding: var(--space-2) var(--space-3);
  color: var(--text-secondary);
  background: var(--neutral-50);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.md-content :deep(code) {
  background: var(--neutral-100);
  color: var(--error-600);
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.md-content :deep(pre) {
  background: var(--neutral-900);
  color: var(--neutral-100);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  overflow-x: auto;
  margin: var(--space-3) 0;
  
  code {
    background: transparent !important;
    color: inherit;
    padding: 0;
    font-size: var(--text-xs);
  }
}

.md-content :deep(table) {
  border-collapse: collapse;
  margin: var(--space-3) 0;
  width: 100%;
}

.md-content :deep(th),
.md-content :deep(td) {
  border: 1px solid var(--border-light);
  padding: var(--space-2) var(--space-3);
  text-align: left;
}

.md-content :deep(th) {
  background: var(--neutral-50);
  font-weight: var(--font-semibold);
}

.md-content :deep(a) {
  color: var(--primary-600);
  text-decoration: none;
  
  &:hover {
    text-decoration: underline;
  }
}

.md-content :deep(.typing-cursor) {
  display: inline-block;
  margin-left: 1px;
  color: var(--success-500);
  font-weight: bold;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

/* ============= 输入区 ============= */
.input-area {
  border-top: 1px solid var(--border-light);
  padding: var(--space-4) var(--space-5) var(--space-5);
  background: var(--bg-primary);
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--space-3);
}

.input-actions .meta {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.input-actions .actions {
  display: flex;
  gap: var(--space-2);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .chat-page {
    grid-template-columns: 260px 1fr;
  }
  
  .sel-model,
  .sel-key {
    width: 200px;
  }
}

@media (max-width: 768px) {
  .chat-page {
    display: flex;
    flex-direction: column;
    height: calc(100dvh - var(--header-height) - 96px);
    min-height: 620px;
  }
  
  .convo-pane {
    flex: 0 0 auto;
    max-height: 220px;
    border-radius: var(--radius-lg);
  }

  .convo-head {
    padding: var(--space-3) var(--space-4);
  }

  .convo-list {
    max-height: 164px;
  }

  .chat-main {
    min-height: 0;
    flex: 1;
    border-radius: var(--radius-lg);
  }
  
  .toolbar {
    flex-direction: column;
    align-items: stretch;
    padding: var(--space-3);
  }
  
  .toolbar .left {
    flex-direction: column;
    align-items: stretch;
  }
  
  .sel-model,
  .sel-key {
    width: 100%;
  }
  
  .messages {
    padding: var(--space-4);
    min-height: 0;
  }
  
  .empty-icon {
    width: 88px;
    height: 88px;
    margin-bottom: var(--space-4);
  }

  .empty h3 {
    font-size: var(--text-lg);
    text-align: center;
  }

  .empty p {
    text-align: center;
    padding-inline: var(--space-4);
  }

  .input-area {
    padding: var(--space-3);
  }

  .input-actions {
    align-items: flex-start;
    gap: var(--space-2);
  }

  .input-actions .meta {
    min-width: 0;
    word-break: break-all;
  }

  .input-actions .actions {
    flex-shrink: 0;
  }
}

@media (max-width: 480px) {
  .chat-page {
    min-height: 560px;
  }

  .convo-pane {
    max-height: 190px;
  }

  .convo-list {
    max-height: 134px;
  }

  .toolbar .right {
    display: none;
  }
}
</style>
