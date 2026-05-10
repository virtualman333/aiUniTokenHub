<template>
  <div class="model-management">
    <!-- 标签页 -->
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="模型管理" name="models">
        <div class="page-header">
          <h2>AI模型管理</h2>
          <div class="header-actions">
            <el-button type="primary" @click="openModelForm()">
              <i class="icon-plus"></i> 添加模型
            </el-button>
          </div>
        </div>

        <!-- 筛选栏 -->
        <div class="filter-bar">
          <div class="filter-row">
            <div class="filter-group">
              <el-select v-model="filterStatus" placeholder="状态" clearable @change="fetchModels" style="width: 110px">
                <el-option label="全部状态" value="" />
                <el-option label="已上架" value="active" />
                <el-option label="已下架" value="inactive" />
                <el-option label="测试中" value="beta" />
              </el-select>
              <el-select v-model="filterProvider" placeholder="供应商" clearable @change="fetchModels" style="width: 130px">
                <el-option label="全部供应商" value="" />
                <el-option 
                  v-for="p in providers" 
                  :key="p.id" 
                  :label="p.name" 
                  :value="p.id" 
                />
              </el-select>
              <el-select v-model="filterHasAccounts" placeholder="账号" clearable @change="fetchModels" style="width: 110px">
                <el-option label="全部" value="" />
                <el-option label="已配置" value="true" />
                <el-option label="未配置" value="false" />
              </el-select>
            </div>
            <el-input 
              v-model="searchQuery" 
              placeholder="搜索模型名称" 
              clearable
              @input="debounceSearch"
              style="width: 180px"
              :prefix-icon="Search"
            />
          </div>
          <!-- 批量操作 -->
          <div class="batch-actions" v-if="selectedModels.length > 0">
            <span class="selected-count">已选择 {{ selectedModels.length }} 项</span>
            <el-button size="small" type="warning" @click="batchToggleStatus">
              批量{{ allSelectedActive ? '下架' : '上架' }}
            </el-button>
            <el-button size="small" type="danger" @click="batchDelete">
              批量删除
            </el-button>
          </div>
        </div>

        <!-- 模型列表 -->
        <el-table 
          :data="models" 
          v-loading="loading"
          stripe
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="name" label="模型名称" min-width="180">
            <template #default="{ row }">
              <div class="model-cell">
                <span class="model-name">{{ row.name }}</span>
                <span class="model-code">{{ row.code }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="provider_name" label="供应商" width="150">
            <template #default="{ row }">
              <el-tag size="small">{{ row.provider_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="定价 (元/1M)" width="220">
            <template #default="{ row }">
              <div class="price-cell">
                <span>输入: ¥{{ Number(row.input_price || 0).toFixed(2) }}</span>
                <span v-if="Number(row.cached_input_price) > 0" class="cached">
                  缓存: ¥{{ Number(row.cached_input_price).toFixed(2) }}
                </span>
                <span>输出: ¥{{ Number(row.output_price || 0).toFixed(2) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="功能" width="200">
            <template #default="{ row }">
              <span v-if="row.supports_vision" class="cap-badge">视觉</span>
              <span v-if="row.supports_streaming" class="cap-badge">流式</span>
              <span v-if="row.supports_tools" class="cap-badge">工具</span>
              <span v-if="row.supports_json" class="cap-badge">JSON</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="账号数量" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.account_count > 0 ? 'success' : 'info'" size="small">
                {{ row.account_count }} 个
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="usage_count" label="调用次数" width="100" sortable />
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="openModelForm(row)">
                编辑
              </el-button>
              <el-button size="small" link type="success" @click="openAccountManager(row)">
                管理账号
              </el-button>
              <el-button size="small" link @click="toggleStatus(row)">
                {{ row.status === 'active' ? '下架' : '上架' }}
              </el-button>
              <el-button size="small" link type="danger" @click="deleteModel(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @size-change="fetchModels"
            @current-change="fetchModels"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 模型表单弹窗 -->
    <el-dialog 
      v-model="formVisible" 
      :title="isEdit ? '编辑模型' : '添加模型'" 
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form 
        ref="formRef" 
        :model="formData" 
        :rules="formRules" 
        label-width="100px"
      >
        <el-form-item label="模型名称" prop="name">
          <el-input v-model="formData.name" placeholder="如: GPT-4 Turbo" />
        </el-form-item>
        
        <el-form-item label="模型代码" prop="code">
          <el-input v-model="formData.code" placeholder="如: gpt-4-turbo" :disabled="isEdit" />
        </el-form-item>
        
        <el-form-item label="供应商" prop="provider">
          <el-select v-model="formData.provider" placeholder="选择供应商" style="width: 100%">
            <el-option 
              v-for="p in providers" 
              :key="p.id" 
              :label="p.name" 
              :value="p.id" 
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="分类" prop="category">
          <el-select v-model="formData.category" placeholder="选择分类" clearable style="width: 100%">
            <el-option 
              v-for="c in categories" 
              :key="c.id" 
              :label="c.name" 
              :value="c.id" 
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="版本" prop="version">
          <el-input v-model="formData.version" placeholder="如: 2024-01-25" />
        </el-form-item>
        
        <el-divider>定价（元 / 百万 tokens）</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="输入价格">
              <el-input-number 
                v-model="formData.input_price" 
                :min="0" 
                :precision="4"
                :step="0.5"
                style="width: 100%"
              />
              <span class="form-tip">元/1M tokens</span>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="缓存命中价格">
              <el-input-number 
                v-model="formData.cached_input_price" 
                :min="0" 
                :precision="4"
                :step="0.1"
                style="width: 100%"
              />
              <span class="form-tip">元/1M tokens；0 时按输入价计费</span>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="输出价格">
              <el-input-number 
                v-model="formData.output_price" 
                :min="0" 
                :precision="4"
                :step="0.5"
                style="width: 100%"
              />
              <span class="form-tip">元/1M tokens</span>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-divider>功能特性</el-divider>
        
        <el-form-item label="功能特性">
          <el-checkbox v-model="formData.supports_streaming">流式输出</el-checkbox>
          <el-checkbox v-model="formData.supports_vision">视觉理解</el-checkbox>
          <el-checkbox v-model="formData.supports_tools">工具调用</el-checkbox>
          <el-checkbox v-model="formData.supports_json">JSON模式</el-checkbox>
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="上下文窗口">
              <el-input-number 
                v-model="formData.context_window" 
                :min="0"
                style="width: 100%"
              />
              <span class="form-tip">tokens</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大输出">
              <el-input-number 
                v-model="formData.max_tokens" 
                :min="0"
                style="width: 100%"
              />
              <span class="form-tip">tokens</span>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-divider>基本信息</el-divider>
        
        <el-form-item label="模型描述">
          <el-input 
            v-model="formData.description" 
            type="textarea" 
            :rows="3"
            placeholder="描述模型的能力和适用场景"
          />
        </el-form-item>
        
        <el-form-item label="标签">
          <el-select 
            v-model="formData.tags" 
            multiple 
            filterable 
            allow-create
            default-first-option
            placeholder="输入标签后按回车"
            style="width: 100%"
          >
            <el-option 
              v-for="tag in commonTags" 
              :key="tag" 
              :label="tag" 
              :value="tag" 
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="状态">
          <el-radio-group v-model="formData.status">
            <el-radio label="active">已上架</el-radio>
            <el-radio label="inactive">已下架</el-radio>
            <el-radio label="beta">测试中</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="标记">
          <el-checkbox v-model="formData.is_featured">推荐</el-checkbox>
          <el-checkbox v-model="formData.is_new">新品</el-checkbox>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 管理上游账号对话框 -->
    <el-dialog
      v-model="accountManagerVisible"
      :title="accountDialogTitle"
      width="900px"
      :close-on-click-modal="false"
    >
      <div class="account-manager">
        <!-- 已关联的账号列表 -->
        <div class="bound-accounts">
          <div class="section-header">
            <h3>已关联账号 - {{ currentModel?.name || '' }}</h3>
            <el-button size="small" type="primary" @click="showAddDialog = true">
              添加账号
            </el-button>
          </div>

          <el-table :data="boundAccounts" v-loading="accountsLoading" stripe size="small">
            <el-table-column prop="account_name" label="账号名称" min-width="150" />
            <el-table-column prop="provider_name" label="供应商" width="120" />
            <el-table-column label="权重" width="120">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.weight"
                  :min="1"
                  :max="100"
                  size="small"
                  style="width: 100px"
                  @change="updateAccountWeight(row)"
                />
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
                  {{ row.is_enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="usage_count" label="使用次数" width="100" align="center" sortable />
            <el-table-column label="操作" width="120" align="center">
              <template #default="{ row }">
                <el-button size="small" link @click="toggleAccount(row)">
                  {{ row.is_enabled ? '禁用' : '启用' }}
                </el-button>
                <el-button size="small" link type="danger" @click="removeAccount(row)">
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!accountsLoading && boundAccounts.length === 0" description="暂无关联账号" />
        </div>
      </div>
    </el-dialog>

    <!-- 添加账号对话框 -->
    <el-dialog
      v-model="showAddDialog"
      title="添加上游账号"
      width="600px"
      :close-on-click-modal="false"
    >
      <div class="add-account-dialog">
        <div class="tip-text" style="margin-bottom: 16px; color: #909399; font-size: 13px;">
          选择要添加到"{{ currentModel?.name }}"的账号：
        </div>
        <el-table
          :data="availableAccounts"
          v-loading="availableLoading"
          stripe
          size="small"
          @selection-change="handleAccountSelection"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="name" label="账号名称" min-width="150" />
          <el-table-column prop="provider_name" label="供应商" width="120" />
          <el-table-column prop="base_url" label="API地址" min-width="200">
            <template #default="{ row }">
              <span style="font-size: 12px; word-break: break-all;">{{ row.base_url }}</span>
            </template>
          </el-table-column>
        </el-table>

        <div style="margin-top: 16px;">
          <span style="margin-right: 16px;">权重：</span>
          <el-input-number
            v-model="addWeight"
            :min="1"
            :max="100"
            size="small"
          />
        </div>
      </div>

      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addAccounts" :loading="adding">
          确定添加（{{ selectedAccounts.length }}个）
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import api from '@/stores'

const activeTab = ref('models')
const loading = ref(false)
const models = ref([])
const providers = ref([])
const categories = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchQuery = ref('')
const filterStatus = ref('')
const filterProvider = ref('')
const filterHasAccounts = ref('')
const selectedModels = ref([])

const defaultFormData = () => ({
  id: null,
  name: '',
  code: '',
  provider: null,
  category: null,
  version: '',
  input_price: 0,
  output_price: 0,
  cached_input_price: 0,
  supports_streaming: true,
  supports_vision: false,
  supports_tools: false,
  supports_json: false,
  context_window: 4096,
  max_tokens: 2048,
  description: '',
  tags: [],
  status: 'active',
  is_featured: false,
  is_new: false
})

const formData = ref({ ...defaultFormData() })
const formVisible = ref(false)
const formRef = ref()
const isEdit = ref(false)
const submitting = ref(false)

const formRules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入模型代码', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择供应商', trigger: 'change' }]
}

const commonTags = ['免费', 'GPT-4', 'Claude', 'Gemini', '国产', '开源', '大语言模型', '视觉模型']

let searchTimer = null

// 管理上游账号相关
const accountManagerVisible = ref(false)
const showAddDialog = ref(false)
const currentModel = ref(null)
const boundAccounts = ref([])
const availableAccounts = ref([])
const accountsLoading = ref(false)
const availableLoading = ref(false)
const selectedAccounts = ref([])
const addWeight = ref(1)
const adding = ref(false)

onMounted(async () => {
  // 并行加载模型列表、供应商和分类
  await Promise.all([
    fetchModels(),
    fetchProviders(),
    fetchCategories()
  ])
})

async function fetchModels() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (searchQuery.value) params.search = searchQuery.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterProvider.value) params.provider_id = filterProvider.value
    if (filterHasAccounts.value !== '' && filterHasAccounts.value != null) {
      params.has_accounts = String(filterHasAccounts.value)
    }
    
    // 后端已直接返回 has_accounts 和 account_count 字段
    const res = await api.get('/models/models/', { params })
    models.value = res.results || res
    total.value = res.total ?? res.count ?? models.value.length
  } catch (e) {
    console.error('获取模型列表失败:', e)
  } finally {
    loading.value = false
  }
}

async function fetchProviders() {
  try {
    const res = await api.get('/models/providers/')
    providers.value = res.results || res || []
  } catch (e) {
    console.error('获取供应商失败:', e)
  }
}

async function fetchCategories() {
  try {
    const res = await api.get('/models/categories/')
    categories.value = res.results || res || []
  } catch (e) {
    console.error('获取分类失败:', e)
  }
}

function debounceSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    fetchModels()
  }, 300)
}

// 批量选择处理
function handleSelectionChange(selection) {
  selectedModels.value = selection
}

// 管理上游账号
async function openAccountManager(row) {
  currentModel.value = row
  accountManagerVisible.value = true
  await fetchBoundAccounts()
}

async function fetchBoundAccounts() {
  accountsLoading.value = true
  try {
    const res = await api.get(`/models/model-upstream/model/${currentModel.value.id}/`)
    boundAccounts.value = res || []
  } catch (e) {
    console.error('获取关联账号失败:', e)
    ElMessage.error('获取关联账号失败')
  } finally {
    accountsLoading.value = false
  }
}

async function fetchAvailableAccounts() {
  availableLoading.value = true
  try {
    const res = await api.get('/models/upstream-accounts/', { params: { page_size: 1000 } })
    const allAccounts = res.results || res || []
    // 过滤掉已关联的账号
    const boundIds = new Set(boundAccounts.value.map(a => a.account_id))
    availableAccounts.value = allAccounts.filter(a => !boundIds.has(a.id))
  } catch (e) {
    console.error('获取可用账号失败:', e)
  } finally {
    availableLoading.value = false
  }
}

async function updateAccountWeight(row) {
  try {
    await api.patch(`/models/model-upstream/${row.id}/weight/`, { weight: row.weight })
    ElMessage.success('权重已更新')
  } catch (e) {
    ElMessage.error('更新权重失败')
    await fetchBoundAccounts() // 刷新恢复
  }
}

async function toggleAccount(row) {
  try {
    const res = await api.post(`/models/model-upstream/${row.id}/toggle/`)
    row.is_enabled = res.is_enabled
    ElMessage.success(res.message)
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function removeAccount(row) {
  try {
    await ElMessageBox.confirm(
      `确定要移除账号 "${row.account_name}" 与模型 "${currentModel.value?.name}" 的关联吗？`,
      '移除确认',
      { type: 'warning' }
    )
    await api.delete('/models/model-upstream/batch-remove/', {
      data: { binding_ids: [row.id] }
    })
    ElMessage.success('移除成功')
    await fetchBoundAccounts()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('移除失败')
    }
  }
}

function handleAccountSelection(selection) {
  selectedAccounts.value = selection
}

async function addAccounts() {
  if (selectedAccounts.value.length === 0) {
    ElMessage.warning('请选择要添加的账号')
    return
  }
  
  adding.value = true
  try {
    const account_ids = selectedAccounts.value.map(a => a.id)
    const res = await api.post('/models/model-upstream/batch-add/', {
      model_id: currentModel.value.id,
      account_ids: account_ids,
      weight: addWeight.value
    })
    ElMessage.success(`成功添加 ${res.created} 个账号`)
    showAddDialog.value = false
    selectedAccounts.value = []
    await fetchBoundAccounts()
  } catch (e) {
    ElMessage.error(e.message || '添加失败')
  } finally {
    adding.value = false
  }
}

// 监听添加对话框显示
watch(showAddDialog, (newVal) => {
  if (newVal) {
    addWeight.value = 1
    selectedAccounts.value = []
    fetchAvailableAccounts()
  }
})

// 计算是否所有选中项都是上架状态
const allSelectedActive = computed(() => {
  return selectedModels.value.every(m => m.status === 'active')
})

// 管理账号对话框标题
const accountDialogTitle = computed(() => {
  return `管理上游账号 - ${currentModel.value?.name || ''}`
})

// 批量删除
async function batchDelete() {
  if (!selectedModels.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedModels.value.length} 个模型吗？此操作不可恢复。`,
      '批量删除确认',
      { type: 'warning' }
    )
    const ids = selectedModels.value.map(m => m.id)
    await api.post('/models/models/batch_delete/', { ids })
    ElMessage.success('批量删除成功')
    selectedModels.value = []
    fetchModels()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '批量删除失败')
    }
  }
}

// 批量切换上下架状态
async function batchToggleStatus() {
  if (!selectedModels.value.length) return
  const newStatus = allSelectedActive ? 'inactive' : 'active'
  try {
    await ElMessageBox.confirm(
      `确定要将选中的 ${selectedModels.value.length} 个模型${newStatus === 'active' ? '上架' : '下架'}吗？`,
      '批量操作确认',
      { type: 'warning' }
    )
    const ids = selectedModels.value.map(m => m.id)
    await api.post('/models/models/batch_toggle_status/', { ids, status: newStatus })
    ElMessage.success(`成功${newStatus === 'active' ? '上架' : '下架'} ${ids.length} 个模型`)
    selectedModels.value = []
    fetchModels()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '批量操作失败')
    }
  }
}

function openModelForm(model = null) {
  if (model) {
    isEdit.value = true
    // 兼容列表返回的 ID 与详情返回的嵌套对象两种格式
    const providerId =
      model.provider && typeof model.provider === 'object'
        ? model.provider.id
        : model.provider ?? null
    const categoryId =
      model.category && typeof model.category === 'object'
        ? model.category.id
        : model.category ?? null
    formData.value = {
      id: model.id,
      name: model.name,
      code: model.code,
      provider: providerId,
      category: categoryId,
      version: model.version || '',
      input_price: parseFloat(model.input_price) || 0,
      output_price: parseFloat(model.output_price) || 0,
      cached_input_price: parseFloat(model.cached_input_price) || 0,
      supports_streaming: model.supports_streaming,
      supports_vision: model.supports_vision,
      supports_tools: model.supports_tools,
      supports_json: model.supports_json,
      context_window: model.context_window,
      max_tokens: model.max_tokens,
      description: model.description || '',
      tags: [...(model.tags || [])],
      status: model.status,
      is_featured: model.is_featured,
      is_new: model.is_new
    }
  } else {
    isEdit.value = false
    formData.value = { ...defaultFormData() }
  }
  formVisible.value = true
}

async function submitForm() {
  try {
    await formRef.value.validate()
  } catch (e) {
    return
  }
  
  submitting.value = true
  try {
    const data = { ...formData.value }
    if (isEdit.value) {
      await api.patch(`/models/models/${data.id}/`, data)
      ElMessage.success('模型更新成功')
    } else {
      await api.post('/models/models/', data)
      ElMessage.success('模型添加成功')
    }
    formVisible.value = false
    fetchModels()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(model) {
  try {
    await api.post(`/models/models/${model.id}/toggle_status/`)
    ElMessage.success('状态已更新')
    fetchModels()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function toggleFeatured(model) {
  try {
    await api.post(`/models/models/${model.id}/set_featured/`, {
      featured: model.is_featured
    })
    ElMessage.success('推荐状态已更新')
  } catch (e) {
    model.is_featured = !model.is_featured
    ElMessage.error('操作失败')
  }
}

async function deleteModel(model) {
  try {
    await ElMessageBox.confirm(
      `确定要删除模型 "${model.name}" 吗？此操作不可恢复。`,
      '删除确认',
      { type: 'warning' }
    )
    await api.delete(`/models/models/${model.id}/`)
    ElMessage.success('删除成功')
    fetchModels()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function getStatusText(status) {
  const map = {
    active: '已上架',
    inactive: '已下架',
    beta: '测试中'
  }
  return map[status] || status
}

function getStatusType(status) {
  const map = {
    active: 'success',
    inactive: 'info',
    beta: 'warning'
  }
  return map[status] || ''
}
</script>

<style scoped>
.model-management {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: white;
  padding: 20px 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 16px 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  flex-wrap: wrap;
}

.filter-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  gap: 8px;
  align-items: center;
}

.batch-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}

.selected-count {
  color: #409eff;
  font-size: 13px;
  margin-right: 8px;
  font-weight: 500;
}

.model-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-cell .model-name {
  font-weight: 600;
  color: #303133;
}

.model-cell .model-code {
  font-size: 12px;
  color: #909399;
  font-family: 'Monaco', 'Menlo', monospace;
}

.price-cell {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  color: #606266;
  gap: 2px;
}

.price-cell .cached {
  color: #10b981;
}

.cap-badge {
  display: inline-block;
  padding: 2px 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  font-size: 11px;
  margin-right: 4px;
  font-weight: 500;
}

.cap-badge:nth-child(2) {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.cap-badge:nth-child(3) {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.cap-badge:nth-child(4) {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

.account-name {
  font-weight: 600;
  color: #303133;
}

.account-pool-config {
  padding: 0;
}

.config-header {
  margin-bottom: 16px;
}

.add-account-form {
  padding: 16px;
}

/* 统计卡片 */
:deep(.el-card) {
  border: none;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

:deep(.el-table) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.el-table th) {
  background: #fafafa !important;
  color: #606266;
  font-weight: 600;
}

:deep(.el-tag) {
  border-radius: 6px;
}

/* 按钮样式优化 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%);
}
/* 管理账号对话框样式 */
.account-manager {
  min-height: 200px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.bound-accounts {
  margin-bottom: 20px;
}

.add-account-dialog {
  padding: 0;
}

.tip-text {
  color: #909399;
  font-size: 13px;
}
</style>
