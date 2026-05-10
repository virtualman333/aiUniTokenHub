<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">上游账号管理</h2>
      <div class="header-actions">
        <el-button @click="syncAllModels" :loading="syncing">
          <el-icon><Refresh /></el-icon>
          同步所有模型
        </el-button>
        <el-button type="primary" @click="showDialog('add')">
          <el-icon><Plus /></el-icon>
          添加账号
        </el-button>
      </div>
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
            <div class="stat-value">{{ Number(stats.avg_success_rate || 0).toFixed(1) }}%</div>
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
      <el-table-column prop="protocol" label="协议" width="120">
        <template #default="{ row }">
          <el-tag>{{ protocolLabel(row.protocol) }}</el-tag>
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
          <el-tag :type="row.is_available ? 'success' : 'danger'">
            {{ row.is_available ? '可用' : '不可用' }}
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
            {{ Number(row.success_rate || 0).toFixed(1) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="avg_latency" label="平均延迟" width="100" align="center">
        <template #default="{ row }">
          {{ row.avg_latency || 0 }}ms
        </template>
      </el-table-column>
      <el-table-column label="绑定模型" width="100" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="showModelList(row)">
            {{ row.model_count || 0 }} 个
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="success" text @click="syncModels(row)">
            同步模型
          </el-button>
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
      :title="isEdit ? '编辑账号' : '添加账号'" 
      width="600px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="渠道名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：OpenAI-官方渠道" />
        </el-form-item>
        <el-form-item label="供应商" prop="provider">
          <el-select v-model="form.provider" placeholder="选择供应商" style="width: 100%">
            <el-option
              v-for="p in providers"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="协议" prop="protocol">
          <el-select v-model="form.protocol" placeholder="选择协议" style="width: 100%" @change="handleProtocolChange">
            <el-option
              v-for="item in protocolOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-alert
          v-if="form.protocol === 'anthropic'"
          title="Anthropic base_url 建议填写 https://api.anthropic.com"
          type="info"
          :closable="false"
          class="protocol-tip"
        />
        <el-form-item label="基础URL" prop="base_url">
          <el-input v-model="form.base_url" :placeholder="baseUrlPlaceholder" />
        </el-form-item>
        <el-form-item label="API Key" prop="api_key">
          <el-input 
            v-model="form.api_key" 
            type="password" 
            show-password
            placeholder="sk-..." 
          />
        </el-form-item>
        <el-form-item label="代理地址" prop="proxy_url">
          <el-input 
            v-model="form.proxy_url" 
            placeholder="留空则直连（如: http://proxy:8080）" 
          />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最大RPM" prop="max_rpm">
              <el-input-number v-model="form.max_rpm" :min="1" :max="100000" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大TPM" prop="max_tpm">
              <el-input-number v-model="form.max_tpm" :min="1" :max="10000000" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="排序" prop="order">
              <el-input-number v-model="form.order" :min="0" :max="1000" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 绑定模型列表弹窗 -->
    <el-dialog v-model="modelListVisible" :title="`${currentChannelName} - 绑定模型列表`" width="700px" destroy-on-close>
      <el-table :data="modelList" v-loading="modelListLoading" stripe>
        <el-table-column prop="name" label="模型名称" min-width="150">
          <template #default="{ row }">
            <span>{{ row.name }}</span>
            <span style="color: #909399; font-size: 12px; margin-left: 6px;">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="provider_name" label="供应商" width="120" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '已上架' : '未上架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="定价(元/1M)" width="180">
          <template #default="{ row }">
            <span style="font-size: 12px;">入:¥{{ Number(row.input_price || 0).toFixed(2) }}</span>
            <span style="font-size: 12px; margin-left: 6px;">出:¥{{ Number(row.output_price || 0).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="usage_count" label="使用次数" width="100" align="center" />
      </el-table>
      <template #footer>
        <el-button @click="modelListVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Connection, Refresh } from '@element-plus/icons-vue'
import api from '@/stores'

const channels = ref([])
const providers = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const syncing = ref(false)
const formRef = ref()

const defaultForm = () => ({
  id: null,
  name: '',
  provider: null,
  protocol: 'openai',
  base_url: '',
  api_key: '',
  proxy_url: '',
  max_rpm: 60,
  max_tpm: 100000,
  is_active: true,
  order: 0
})

const form = ref({ ...defaultForm() })

const protocolOptions = [
  { label: 'OpenAI兼容', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'Gemini', value: 'gemini' }
]

const baseUrlPlaceholder = computed(() => (
  form.value.protocol === 'anthropic'
    ? 'https://api.anthropic.com'
    : 'https://api.openai.com/v1'
))

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
    const res = await api.get('/models/upstream-accounts/')
    channels.value = res.results || res || []
    
    // 计算统计
    stats.value.total_channels = channels.value.length
    stats.value.active_channels = channels.value.filter(c => c.is_active).length
    stats.value.total_calls = channels.value.reduce((sum, c) => sum + (c.total_calls || 0), 0)
    if (channels.value.length > 0) {
      stats.value.avg_success_rate = channels.value.reduce((sum, c) => sum + (c.success_rate || 100), 0) / channels.value.length
    }
  } catch (error) {
    console.error('加载账号失败:', error)
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
      provider: row.provider?.id || row.provider_id,
      protocol: row.protocol || 'openai',
      base_url: row.base_url,
      api_key: row.api_key || '',
      proxy_url: row.proxy_url || '',
      max_rpm: row.max_rpm || 60,
      max_tpm: row.max_tpm || 100000,
      is_active: row.is_active !== false,
      order: row.order || 0
    }
  }
  dialogVisible.value = true
}

const handleProtocolChange = (value) => {
  if (value === 'anthropic' && (!form.value.base_url || form.value.base_url === 'https://api.openai.com/v1')) {
    form.value.base_url = 'https://api.anthropic.com'
  }
}

const protocolLabel = (value) => {
  return protocolOptions.find(item => item.value === value)?.label || 'OpenAI兼容'
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  submitting.value = true
  try {
    if (isEdit.value) {
      await api.put(`/models/upstream-accounts/${form.value.id}/`, form.value)
      ElMessage.success('更新成功')
    } else {
      const res = await api.post('/models/upstream-accounts/', form.value)
      ElMessage.success(res.msg || '添加成功')
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
  ElMessage.info('正在测试连接...')
  try {
    const res = await api.post(`/models/upstream-accounts/${row.id}/test_connection/`)
    if (res.success !== false) {
      ElMessage.success('连接成功')
    } else {
      ElMessage.error(res.msg || '连接失败')
    }
  } catch (error) {
    ElMessage.error('测试请求失败')
  }
}

const syncModels = async (row) => {
  try {
    await ElMessageBox.confirm(
      `将从 "${row.name}" 同步模型列表到数据库。已存在的模型将跳过。`,
      '同步模型',
      { type: 'info' }
    )
    const res = await api.post(`/models/upstream-accounts/${row.id}/sync_models/`)
    ElMessage.success(res.msg || `成功同步 ${res.data?.added || 0} 个模型`)
    loadChannels()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('同步失败')
    }
  }
}

const syncAllModels = async () => {
  syncing.value = true
  let totalAdded = 0
  let successCount = 0
  let failCount = 0
  
  try {
    for (const channel of channels.value) {
      try {
        const res = await api.post(`/models/upstream-accounts/${channel.id}/sync_models/`)
        if (res.success !== false) {
          totalAdded += res.data?.added || 0
          successCount++
        } else {
          failCount++
        }
      } catch (e) {
        failCount++
      }
    }
    ElMessage.success(`同步完成：成功 ${successCount} 个账号，新增 ${totalAdded} 个模型${failCount > 0 ? `（${failCount} 个失败）` : ''}`)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('同步失败')
    }
  } finally {
    syncing.value = false
  }
}

const deleteChannel = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这个账号吗？', '警告', { type: 'warning' })
    await api.delete(`/models/upstream-accounts/${row.id}/`)
    ElMessage.success('删除成功')
    loadChannels()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 绑定模型列表
const modelListVisible = ref(false)
const modelList = ref([])
const modelListLoading = ref(false)
const currentChannelName = ref('')

async function showModelList(row) {
  currentChannelName.value = row.name
  modelListVisible.value = true
  await loadModelList(row.id)
}

async function loadModelList(accountId) {
  modelListLoading.value = true
  try {
    const res = await api.get(`/models/upstream-accounts/${accountId}/model_list/`)
    modelList.value = res.data || res || []
  } catch (error) {
    modelList.value = []
    ElMessage.error('获取模型列表失败')
  } finally {
    modelListLoading.value = false
  }
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
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

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

.protocol-tip {
  margin-bottom: 18px;
}
</style>
