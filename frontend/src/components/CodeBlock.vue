<template>
  <div class="code-block-wrapper">
    <div class="code-header">
      <span class="language">{{ language }}</span>
      <el-button size="small" text @click="copyCode" class="copy-btn">
        <el-icon><DocumentCopy /></el-icon> 复制
      </el-button>
    </div>
    <pre><code :class="['hljs', language]" v-html="highlightedCode"></code></pre>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentCopy } from '@element-plus/icons-vue'
import hljs from 'highlight.js/lib/core'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import powershell from 'highlight.js/lib/languages/powershell'
import plaintext from 'highlight.js/lib/languages/plaintext'
import ini from 'highlight.js/lib/languages/ini'

// 注册所需语言
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('powershell', powershell)
hljs.registerLanguage('text', plaintext)
hljs.registerLanguage('ini', ini)

// 不引入全局 theme CSS，避免与 markdown.ts 的 github.css 冲突
// 深色主题样式写在下方 scoped style 中

const props = defineProps({
  code: {
    type: String,
    required: true
  },
  language: {
    type: String,
    default: 'text'
  }
})

const highlightedCode = computed(() => {
  if (props.language && hljs.getLanguage(props.language)) {
    try {
      return hljs.highlight(props.code, { language: props.language }).value
    } catch (e) {
      console.warn('Code highlighting failed:', e)
    }
  }
  return hljs.highlightAuto(props.code).value
})

function copyCode() {
  // 尝试使用 Clipboard API（需要 HTTPS 安全上下文）
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(props.code).then(() => {
      ElMessage.success('代码已复制到剪贴板')
    }).catch(() => {
      fallbackCopy()
    })
  } else {
    fallbackCopy()
  }
}

function fallbackCopy() {
  // 使用 textarea + execCommand 作为 fallback（支持 HTTP 环境）
  const textarea = document.createElement('textarea')
  textarea.value = props.code
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '-9999px'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()
  try {
    document.execCommand('copy')
    ElMessage.success('代码已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
  document.body.removeChild(textarea)
}
</script>

<style scoped>
.code-block-wrapper {
  margin: 16px 0;
  border-radius: 8px;
  overflow: hidden;
  background-color: #282c34;
  border: 1px solid #dcdfe6;
}

.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #dcdfe6;
}

.language {
  font-size: 12px;
  color: #909399;
  text-transform: uppercase;
  font-weight: bold;
}

.copy-btn {
  color: #606266;
}

.copy-btn:hover {
  color: #409eff;
}

pre {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
}

code {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  background: transparent !important;
}

/* atom-one-dark 语法高亮（scoped，不污染全局 .hljs） */
.code-block-wrapper :deep(.hljs) {
  color: #abb2bf;
  background: #282c34;
}
.code-block-wrapper :deep(.hljs-comment),
.code-block-wrapper :deep(.hljs-quote) {
  color: #5c6370;
  font-style: italic;
}
.code-block-wrapper :deep(.hljs-doctag),
.code-block-wrapper :deep(.hljs-keyword),
.code-block-wrapper :deep(.hljs-formula) {
  color: #c678dd;
}
.code-block-wrapper :deep(.hljs-section),
.code-block-wrapper :deep(.hljs-name),
.code-block-wrapper :deep(.hljs-selector-tag),
.code-block-wrapper :deep(.hljs-deletion),
.code-block-wrapper :deep(.hljs-subst) {
  color: #e06c75;
}
.code-block-wrapper :deep(.hljs-literal) {
  color: #56b6c2;
}
.code-block-wrapper :deep(.hljs-string),
.code-block-wrapper :deep(.hljs-regexp),
.code-block-wrapper :deep(.hljs-addition),
.code-block-wrapper :deep(.hljs-attribute),
.code-block-wrapper :deep(.hljs-meta .hljs-string) {
  color: #98c379;
}
.code-block-wrapper :deep(.hljs-attr),
.code-block-wrapper :deep(.hljs-variable),
.code-block-wrapper :deep(.hljs-template-variable),
.code-block-wrapper :deep(.hljs-type),
.code-block-wrapper :deep(.hljs-selector-class),
.code-block-wrapper :deep(.hljs-selector-attr),
.code-block-wrapper :deep(.hljs-selector-pseudo),
.code-block-wrapper :deep(.hljs-number) {
  color: #d19a66;
}
.code-block-wrapper :deep(.hljs-symbol),
.code-block-wrapper :deep(.hljs-bullet),
.code-block-wrapper :deep(.hljs-link),
.code-block-wrapper :deep(.hljs-meta),
.code-block-wrapper :deep(.hljs-selector-id),
.code-block-wrapper :deep(.hljs-title) {
  color: #61aeee;
}
.code-block-wrapper :deep(.hljs-built_in),
.code-block-wrapper :deep(.hljs-title.class_),
.code-block-wrapper :deep(.hljs-class .hljs-title) {
  color: #e6c07b;
}
.code-block-wrapper :deep(.hljs-emphasis) {
  font-style: italic;
}
.code-block-wrapper :deep(.hljs-strong) {
  font-weight: 700;
}
.code-block-wrapper :deep(.hljs-link) {
  text-decoration: underline;
}
</style>
