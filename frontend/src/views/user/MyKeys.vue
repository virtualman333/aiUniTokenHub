<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">我的密钥</h2>
      <el-button type="primary" @click="showCreateDialog = true">创建密钥</el-button>
    </div>
    
    <el-table :data="apiKeys" v-loading="loading">
      <el-table-column prop="name" label="名称" />
      <el-table-column label="密钥" width="300">
        <template #default="{ row }">
          <div class="key-display">
            <span v-if="!row.show">{{ maskedKey(row.key) }}</span>
            <span v-else class="key-value">{{ row.key }}</span>
            <el-button size="small" text @click="row.show = !row.show">
              <el-icon><View v-if="!row.show" /><Hide v-else /></el-icon>
            </el-button>
            <el-button size="small" text @click="copyKey(row.key)">
              <el-icon><DocumentCopy /></el-icon>
            </el-button>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="rate_limit" label="限流(/min)" width="100" align="center" />
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_expired ? 'danger' : row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_expired ? '已过期' : row.is_active ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" align="center">
        <template #default="{ row }">
          <el-button size="small" type="danger" text @click="revokeKey(row)">撤销</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 创建密钥对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建API密钥" width="500px">
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
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createKey">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/stores'
import dayjs from 'dayjs'

const apiKeys = ref([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const formRef = ref()

const form = reactive({
  name: '',
  rate_limit: 60,
  expires_at: null,
  allow_ips: ''
})

const rules = {
  name: [{ required: true, message: '请输入密钥名称', trigger: 'blur' }]
}

onMounted(() => {
  loadKeys()
})

const loadKeys = async () => {
  loading.value = true
  try {
    const res = await api.get('/users/keys/')
    apiKeys.value = res.results || res
    apiKeys.value.forEach(k => k.show = false)
  } catch (error) {
    ElMessage.error('加载密钥失败')
  } finally {
    loading.value = false
  }
}

const maskedKey = (key) => {
  return key.substring(0, 8) + '...' + key.substring(key.length - 4)
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

const copyKey = async (key) => {
  await navigator.clipboard.writeText(key)
  ElMessage.success('密钥已复制')
}

const createKey = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  creating.value = true
  try {
    await api.post('/users/keys/', {
      ...form,
      expires_at: form.expires_at ? form.expires_at.toISOString() : null
    })
    ElMessage.success('密钥创建成功')
    showCreateDialog.value = false
    loadKeys()
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

const revokeKey = async (key) => {
  try {
    await ElMessageBox.confirm('确定要撤销此密钥吗？撤销后无法恢复。', '提示', {
      type: 'warning'
    })
    await api.delete(`/users/keys/${key.id}/`)
    ElMessage.success('密钥已撤销')
    loadKeys()
  } catch {
    // 取消操作
  }
}
</script>

<style lang="scss" scoped>
.key-display {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .key-value {
    font-family: monospace;
    color: #409EFF;
  }
}
</style>
