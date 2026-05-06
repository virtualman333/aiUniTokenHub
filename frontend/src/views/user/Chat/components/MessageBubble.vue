<template>
  <div class="msg-row" :class="msg.role">
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
        <div
          v-if="msg.role === 'assistant'"
          class="md-content"
          v-html="htmlContent"
        />
        <div v-else class="msg-content user-content">
          {{ msg.content }}
        </div>
      </template>
      <div v-if="msg.role === 'assistant' && !msg.pending && msg.content" class="msg-actions">
        <el-button text size="small" @click="$emit('copy', msg.content)">
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
            <div v-if="cachedTokens > 0" class="td-row sub">
              <span>└ 缓存命中</span>
              <strong>{{ cachedTokens }}</strong>
            </div>
            <div v-if="promptAudio > 0" class="td-row sub">
              <span>└ 语音输入</span>
              <strong>{{ promptAudio }}</strong>
            </div>
            <div class="td-row">
              <span>输出 (completion)</span>
              <strong>{{ msg.completion_tokens || 0 }}</strong>
            </div>
            <div v-if="reasoningTokens > 0" class="td-row sub">
              <span>└ 推理 (reasoning)</span>
              <strong>{{ reasoningTokens }}</strong>
            </div>
            <div v-if="acceptedPrediction > 0" class="td-row sub">
              <span>└ 预测命中</span>
              <strong>{{ acceptedPrediction }}</strong>
            </div>
            <div v-if="rejectedPrediction > 0" class="td-row sub">
              <span>└ 预测拒绝</span>
              <strong>{{ rejectedPrediction }}</strong>
            </div>
            <div v-if="cacheCreation > 0" class="td-row sub">
              <span>└ 缓存创建 (Anthropic)</span>
              <strong>{{ cacheCreation }}</strong>
            </div>
            <div v-if="cacheRead > 0" class="td-row sub">
              <span>└ 缓存读取 (Anthropic)</span>
              <strong>{{ cacheRead }}</strong>
            </div>
          </div>
        </el-popover>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { User, Cpu, WarningFilled, DocumentCopy, DataLine } from '@element-plus/icons-vue'
import { renderMarkdown } from '@/utils/markdown'

interface Msg {
  role: 'system' | 'user' | 'assistant'
  content: string
  pending?: boolean
  error?: string
  total_tokens?: number
  prompt_tokens?: number
  completion_tokens?: number
  usage?: any
}

const props = defineProps<{ msg: Msg }>()
defineEmits<{ copy: [text: string] }>()

const cursorHtml = '<span class="typing-cursor">▍</span>'

// 仅当 msg.content 或 pending 变化时重新渲染 markdown，
// 不会因为同列表里其它消息变化而被牵连重新计算。
const htmlContent = computed(() => {
  if (props.msg.role !== 'assistant') return ''
  const html = renderMarkdown(props.msg.content || '')
  return props.msg.pending ? html + cursorHtml : html
})

const cachedTokens = computed(() => Number(props.msg.usage?.prompt_tokens_details?.cached_tokens || 0))
const promptAudio = computed(() => Number(props.msg.usage?.prompt_tokens_details?.audio_tokens || 0))
const reasoningTokens = computed(() => Number(props.msg.usage?.completion_tokens_details?.reasoning_tokens || 0))
const acceptedPrediction = computed(() => Number(props.msg.usage?.completion_tokens_details?.accepted_prediction_tokens || 0))
const rejectedPrediction = computed(() => Number(props.msg.usage?.completion_tokens_details?.rejected_prediction_tokens || 0))
const cacheCreation = computed(() => Number(props.msg.usage?.cache_creation_input_tokens || 0))
const cacheRead = computed(() => Number(props.msg.usage?.cache_read_input_tokens || 0))
</script>

<style scoped>
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

/* Markdown 内容样式 */
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
</style>
