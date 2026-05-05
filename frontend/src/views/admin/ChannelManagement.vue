<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">渠道管理</h2>
      <el-button type="primary" @click="showDialog('add')">
        <el-icon><Plus /></el-icon>
        添加渠道
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value">{{ stats.total_channels }}</div>
            <div class="stat-label">总渠道数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value">{{ stats.active_channels }}</div>
            <div class="stat-label">活跃渠道</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value">{{ stats.total_calls }}</div>
            <div class="stat-label">总调用次数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value">{{ stats.avg_success_rate.toFixed(1) }}%</div>
            <div class="stat-label">平均成功率</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 渠道列表 -->
    <el-table :data="channels" v-loading="loading" row-key="id">
      <el-table-column prop="name" label="渠道名称" min-width="150">
        <template #default="{ row }">
          <div class="channel-name">
            <el-icon><Connection /></el-icon>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="provider_name" label="供应商" width="120">
        <template #default="{ row }">
          <el-tag>{{ row.provider_name || row.provider?.name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="base_url" label="基础URL" min-width="200">
        <template #default="{ row }">
          <el-tooltip :content="row.base_url" placement="top">
            <span class="url-text">{{ row.base_url }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ getStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="weight" label="权重" width="80" align="center" />
      <el-table-column prop="max_qps" label="最大QPS" width="100" align="center" />
      <el-table-column prop="total_calls" label="调用次数" width="120" align="center">
        <template #default="{ row }">
          {{ formatNumber(row.total_calls) }}
        </template>
      </el-table-column>
      <el-table-column prop="success_rate" label="成功率" width="100" align="center">
        <template #default="{ row }">
          <span :class="getSuccessRateClass(row.success_rate)">
            {{ row.success_rate?.toFixed(1) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="avg_latency" label="平均延迟" width="100" align="center">
        <template #default="{ row }">
          {{ row.avg_latency || 0 }}ms
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" text @click="testChannel(row)">
            测试
          </el-button>
          <el-button size="small" type="primary" text @click="showDialog('edit', row)">
            编辑
          </el-button>
          <el-button size="small" type="danger" text @click="deleteChannel(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑渠道' : '添加渠道'" 
      width="600px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="渠道名称" prop="name">
          <el-input v-model="form.value.name" placeholder="例如：OpenAI-官方渠道" />
        </el-form-item>
        <el-form-item label="供应商" prop="provider">
          <el-select v-model="form.value.provider" placeholder="选择供应商" style="width: 100%">
            <el-option
              v-for="p in providers"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="基础URL" prop="base_url">
          <el-input v-model="form.value.base_url" placeholder="https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item label="API Key" prop="api_key">
          <el-input 
            v-model="form.value.api_key" 
            type="password" 
            show-password
            placeholder="sk-..." 
          />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="权重" prop="weight">
              <el-input-number v-model="form.value.weight" :min="1" :max="10" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级" prop="priority">
              <el-input-number v-model="form.value.priority" :min="1" :max="1000" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最大QPS" prop="max_qps">
              <el-input-number v-model="form.value.max_qps" :min="1" :max="10000" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.value.status" style="width: 100%">
                <el-option value="active" label="正常" />
                <el-option value="disabled" label="已禁用" />
                <el-option value="maintenance" label="维护中" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="默认渠道">
          <el-switch v-model="form.value.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/stores'

const channels = ref([])
const providers = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref()

const defaultForm = () => ({
  id: null,
  name: '',
  provider: null,
  base_url: '',
  api_key: '',
  weight: 1,
  priority: 100,
  max_qps: 100,
  max_tpm: 100000,
  status: 'active',
  is_default: false
})

const form = ref({ ...defaultForm() })

const rules = {
  name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }],
  base_url: [{ required: true, message: '请输入基础URL', trigger: 'blur' }]
}

const stats = ref({
  total_channels: 0,
  active_channels: 0,
  total_calls: 0,
  avg_success_rate: 100
})

const loadChannels = async () => {
  loading.value = true
  try {
    const res = await api.get('/models/channels/')
    channels.value = res.results || res || []
    
    // 计算统计
    stats.value.total_channels = channels.value.length
    stats.value.active_channels = channels.value.filter(c => c.status === 'active').length
    stats.value.total_calls = channels.value.reduce((sum, c) => sum + (c.total_calls || 0), 0)
    if (channels.value.length > 0) {
      stats.value.avg_success_rate = channels.value.reduce((sum, c) => sum + (c.success_rate || 100), 0) / channels.value.length
    }
  } catch (error) {
    console.error('加载渠道失败:', error)
    channels.value = []
  } finally {
    loading.value = false
  }
}

const loadProviders = async () => {
  try {
    const res = await api.get('/models/providers/')
    providers.value = res.results || res || []
  } catch (error) {
    console.error('加载供应商失败:', error)
  }
}

const showDialog = (type, row = null) => {
  if (type === 'add') {
    isEdit.value = false
    form.value = { ...defaultForm() }
  } else {
    isEdit.value = true
    form.value = {
      id: row.id,
      name: row.name,
      provider: row.provider?.id || row.provider,
      base_url: row.base_url,
      api_key: row.api_key || '',
      weight: row.weight,
      priority: row.priority,
      max_qps: row.max_qps,
      max_tpm: row.max_tpm,
      status: row.status,
      is_default: row.is_default
    }
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  submitting.value = true
  try {
    if (isEdit.value) {
      await api.put(`/models/channels/${form.value.id}/`, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.post('/models/channels/', form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    loadChannels()
  } catch (error) {
    ElMessage.error(isEdit.value ? '更新失败' : '添加失败')
  } finally {
    submitting.value = false
  }
}

const testChannel = async (row) => {
  ElMessage.info('正在测试渠道...')
  try {
    const res = await api.post(`/models/channels/${row.id}/test/`)
    if (res.success) {
      ElMessage.success(`测试成功！响应时间: ${res.latency}ms`)
    } else {
      ElMessage.error(`测试失败: ${res.error}`)
    }
  } catch (error) {
    ElMessage.error('测试请求失败')
  }
}

const deleteChannel = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这个渠道吗？', '警告', { type: 'warning' })
    await api.delete(`/models/channels/${row.id}/`)
    ElMessage.success('删除成功')
    loadChannels()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const getStatusType = (status) => {
  const types = { active: 'success', disabled: 'info', maintenance: 'warning', error: 'danger' }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = { active: '正常', disabled: '已禁用', maintenance: '维护中', error: '异常' }
  return labels[status] || status
}

const getSuccessRateClass = (rate) => {
  if (rate >= 99) return 'text-success'
  if (rate >= 95) return 'text-warning'
  return 'text-danger'
}

const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

onMounted(() => {
  loadChannels()
  loadProviders()
})
</script>

<style scoped>
.stats-row {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
  padding: 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409EFF;
}

.stat-label {
  margin-top: 8px;
  color: #909399;
  font-size: 14px;
}

.channel-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.url-text {
  font-family: monospace;
  font-size: 12px;
  color: #606266;
}

.text-success { color: #67C23A; }
.text-warning { color: #E6A23C; }
.text-danger { color: #F56C6C; }
</style>
