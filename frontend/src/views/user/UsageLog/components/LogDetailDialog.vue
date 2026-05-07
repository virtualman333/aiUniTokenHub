<template>
  <el-dialog v-model="visible" title="请求详情" width="600px">
    <el-descriptions :column="1" border>
      <el-descriptions-item label="API路径">{{ log?.endpoint }}</el-descriptions-item>
      <el-descriptions-item label="请求方法">{{ log?.method }}</el-descriptions-item>
      <el-descriptions-item label="状态码">{{ log?.status_code }}</el-descriptions-item>
      <el-descriptions-item label="响应时间">{{ log?.response_time }}ms</el-descriptions-item>
      <el-descriptions-item label="IP地址">{{ log?.ip_address }}</el-descriptions-item>
      <el-descriptions-item label="时间">{{ formatDate(log?.created_at) }}</el-descriptions-item>
    </el-descriptions>
    
    <template v-if="log?.request_body || log?.response_body || log?.error_message">
      <el-divider />
      
      <div v-if="log?.request_body" class="detail-section">
        <h4>请求体</h4>
        <pre class="detail-code">{{ formatCode(log.request_body) }}</pre>
      </div>
      
      <div v-if="log?.response_body" class="detail-section">
        <h4>响应体</h4>
        <pre class="detail-code">{{ formatCode(log.response_body) }}</pre>
      </div>
      
      <div v-if="log?.error_message" class="detail-section">
        <h4>错误信息</h4>
        <pre class="detail-code error">{{ formatCode(log.error_message) }}</pre>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import dayjs from 'dayjs'

const props = defineProps<{
  modelValue: boolean
  log: any
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const visible = ref(false)

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

function decodeUnicode(str: string) {
  if (!str) return ''
  return str.replace(/\\u([\dA-Fa-f]{4})/g, (match, p1) => {
    return String.fromCharCode(parseInt(p1, 16))
  })
}

function formatCode(content: string) {
  if (!content) return ''
  return decodeUnicode(content)
}

function formatDate(date: string) {
  return date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-'
}
</script>

<style scoped>
.detail-section {
  margin-bottom: 16px;
}

.detail-section h4 {
  margin-bottom: 8px;
  font-size: 14px;
  color: #333;
}

.detail-code {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  max-height: 200px;
  font-family: monospace;
  font-size: 13px;
  margin: 0;
}

.detail-code.error {
  color: #F56C6C;
}
</style>
