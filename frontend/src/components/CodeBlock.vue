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
import { copyToClipboard } from '@/utils/clipboard'

// 注册所需语言
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('powershell', powershell)
hljs.registerLanguage('text', plaintext)
hljs.registerLanguage('ini', ini)

import 'highlight.js/styles/atom-one-dark.css'

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

async function copyCode() {
  const success = await copyToClipboard(props.code)
  if (success) {
    ElMessage.success('代码已复制到剪贴板')
  } else {
    ElMessage.error('复制失败，请手动复制')
  }
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
</style>
