<template>
  <el-dialog v-model="visible" title="创建API密钥" width="500px" @closed="handleClosed">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="密钥名称" prop="name">
        <el-input v-model="form.name" placeholder="例如：我的应用密钥" />
      </el-form-item>
      <el-form-item label="限流" prop="rate_limit">
        <el-input-number v-model="form.rate_limit" :min="1" :max="1000" />
        <span style="margin-left: 8px;">次/分钟</span>
      </el-form-item>
      <el-form-item label="过期时间" prop="expires_at">
        <el-date-picker
          v-model="form.expires_at"
          type="datetime"
          placeholder="不设置则永不过期"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="IP白名单" prop="allow_ips">
        <el-input
          v-model="form.allow_ips"
          type="textarea"
          :rows="2"
          placeholder="留空表示不限制IP，多个IP用逗号分隔"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'submit': [data: { name: string; rate_limit: number; expires_at: string | null; allow_ips: string }]
}>()

const visible = ref(false)
const loading = ref(false)
const formRef = ref()

const form = reactive({
  name: '',
  rate_limit: 60,
  expires_at: null as Date | null,
  allow_ips: ''
})

const rules = {
  name: [{ required: true, message: '请输入密钥名称', trigger: 'blur' }]
}

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

function handleClosed() {
  formRef.value?.resetFields()
  form.expires_at = null
}

function handleCancel() {
  visible.value = false
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  emit('submit', {
    name: form.name,
    rate_limit: form.rate_limit,
    expires_at: form.expires_at?.toISOString() || null,
    allow_ips: form.allow_ips
  })
  visible.value = false
  loading.value = false
}
</script>
