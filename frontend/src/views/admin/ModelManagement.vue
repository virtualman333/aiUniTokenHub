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
          <el-table-column label="定价" width="180">
            <template #default="{ row }">
              <div class="price-cell">
                <span>输入: ¥{{ Number(row.input_price || 0).toFixed(4) }}/1K</span>
                <span>输出: ¥{{ Number(row.output_price || 0).toFixed(4) }}/1K</span>
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
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="openModelForm(row)">
                编辑
              </el-button>
              <el-button size="small" link type="warning" @click="openAccountDialog(row)">
                账号池
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

      <!-- 上游账号管理 -->
      <el-tab-pane label="上游账号池" name="accounts">
        <div class="page-header">
          <h2>上游账号池</h2>
          <div class="header-actions">
            <el-button type="primary" @click="openAccountForm()">
              <i class="icon-plus"></i> 添加账号
            </el-button>
          </div>
        </div>

        <el-table :data="upstreamAccounts" v-loading="loadingAccounts" stripe>
          <el-table-column prop="name" label="账号名称" min-width="150">
            <template #default="{ row }">
              <span class="account-name">{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="provider_name" label="供应商" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.provider_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="base_url" label="API地址" min-width="200" show-overflow-tooltip />
          <el-table-column prop="max_rpm" label="限流(RPM)" width="100" align="center" />
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="可用性" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_available ? 'success' : 'danger'" size="small">
                {{ row.is_available ? '正常' : '异常' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="model_count" label="关联模型" width="100" align="center">
            <template #default="{ row }">
              <el-link type="primary">{{ row.model_count }} 个</el-link>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="openAccountForm(row)">
                编辑
              </el-button>
              <el-button size="small" link type="success" @click="testConnection(row)">
                测试
              </el-button>
              <el-button size="small" link type="danger" @click="deleteAccount(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
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
        
        <el-divider>定价</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="输入价格">
              <el-input-number 
                v-model="formData.input_price" 
                :min="0" 
                :precision="6"
                style="width: 100%"
              />
              <span class="form-tip">元/千tokens</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="输出价格">
              <el-input-number 
                v-model="formData.output_price" 
                :min="0" 
                :precision="6"
                style="width: 100%"
              />
              <span class="form-tip">元/千tokens</span>
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

    <!-- 账号池配置弹窗 -->
    <el-dialog v-model="accountDialogVisible" :title="`配置 ${currentModel?.name} 账号池`" width="800px" destroy-on-close>
      <div class="account-pool-config">
        <div class="config-header">
          <el-button type="primary" @click="showAddAccountPanel = true">
            添加账号到模型
          </el-button>
        </div>

        <el-table :data="modelAccounts" v-loading="loadingModelAccounts" stripe>
          <el-table-column prop="account_name" label="账号名称" />
          <el-table-column prop="account_url" label="API地址" show-overflow-tooltip />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.account_active ? 'success' : 'info'" size="small">
                {{ row.account_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="权重" width="120">
            <template #default="{ row }">
              <el-input-number 
                v-model="row.weight" 
                :min="1" 
                :max="100" 
                size="small"
                @change="updateWeight(row)"
              />
            </template>
          </el-table-column>
          <el-table-column label="启用" width="80">
            <template #default="{ row }">
              <el-switch v-model="row.is_enabled" @change="toggleBinding(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="usage_count" label="使用次数" width="100" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button size="small" link type="danger" @click="removeBinding(row)">
                移除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 添加账号面板 -->
        <el-drawer v-model="showAddAccountPanel" title="添加账号" size="500px">
          <div class="add-account-form">
            <el-form-item label="选择账号">
              <el-select v-model="selectedAccountIds" multiple placeholder="选择上游账号" style="width: 100%">
                <el-option
                  v-for="acc in availableAccounts"
                  :key="acc.id"
                  :label="acc.name"
                  :value="acc.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="权重">
              <el-input-number v-model="newAccountWeight" :min="1" :max="100" />
            </el-form-item>
            <el-button type="primary" @click="addAccountsToModel" :loading="addingAccounts">
              添加
            </el-button>
          </div>
        </el-drawer>
      </div>
    </el-dialog>

    <!-- 上游账号表单弹窗 -->
    <el-dialog v-model="accountFormVisible" :title="isAccountEdit ? '编辑账号' : '添加账号'" width="600px" destroy-on-close>
      <el-form ref="accountFormRef" :model="accountFormData" :rules="accountFormRules" label-width="100px">
        <el-form-item label="账号名称" prop="name">
          <el-input v-model="accountFormData.name" placeholder="如: OpenAI主账号" />
        </el-form-item>
        <el-form-item label="供应商" prop="provider">
          <el-select v-model="accountFormData.provider" placeholder="选择供应商" style="width: 100%">
            <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="API地址" prop="base_url">
          <el-input v-model="accountFormData.base_url" placeholder="如: https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item label="API密钥" prop="api_key">
          <el-input v-model="accountFormData.api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="代理地址" prop="proxy_url">
          <el-input v-model="accountFormData.proxy_url" placeholder="留空则直连" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最大RPM">
              <el-input-number v-model="accountFormData.max_rpm" :min="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大TPM">
              <el-input-number v-model="accountFormData.max_tpm" :min="1000" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="启用">
          <el-switch v-model="accountFormData.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="accountFormVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAccountForm" :loading="submittingAccount">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
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
const filterHasAccounts = ref('true') // 默认只显示已配置账号的模型
const selectedModels = ref([])

// 上游账号相关
const upstreamAccounts = ref([])
const loadingAccounts = ref(false)
const accountDialogVisible = ref(false)
const accountFormVisible = ref(false)
const accountFormRef = ref()
const isAccountEdit = ref(false)
const submittingAccount = ref(false)
const currentModel = ref(null)
const modelAccounts = ref([])
const loadingModelAccounts = ref(false)
const showAddAccountPanel = ref(false)
const selectedAccountIds = ref([])
const newAccountWeight = ref(1)
const addingAccounts = ref(false)
const availableAccounts = ref([])

const defaultFormData = () => ({
  id: null,
  name: '',
  code: '',
  provider: null,
  category: null,
  version: '',
  input_price: 0,
  output_price: 0,
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

const accountFormData = ref({
  id: null,
  name: '',
  provider: null,
  base_url: '',
  api_key: '',
  proxy_url: '',
  max_rpm: 60,
  max_tpm: 100000,
  is_active: true
})

const accountFormRules = {
  name: [{ required: true, message: '请输入账号名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择供应商', trigger: 'change' }],
  base_url: [{ required: true, message: '请输入API地址', trigger: 'blur' }],
  api_key: [{ required: true, message: '请输入API密钥', trigger: 'blur' }]
}

const formRules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入模型代码', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择供应商', trigger: 'change' }]
}

const commonTags = ['免费', 'GPT-4', 'Claude', 'Gemini', '国产', '开源', '大语言模型', '视觉模型']

let searchTimer = null

onMounted(async () => {
  // 并行加载模型列表、供应商和分类
  await Promise.all([
    fetchModels(),
    fetchProviders(),
    fetchCategories()
  ])
})

function onTabChange(tab) {
  if (tab === 'accounts') {
    fetchUpstreamAccounts()
  }
}

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
    if (filterHasAccounts.value) params.has_accounts = filterHasAccounts.value
    
    // 后端已直接返回 has_accounts 和 account_count 字段
    const res = await api.get('/models/models/', { params })
    models.value = res.results || res
    total.value = res.count || models.value.length
  } catch (e) {
    console.error('获取模型列表失败:', e)
  } finally {
    loading.value = false
  }
}

async function fetchUpstreamAccounts() {
  loadingAccounts.value = true
  try {
    const res = await api.get('/models/upstream-accounts/')
    upstreamAccounts.value = res.results || res || []
  } catch (e) {
    console.error('获取上游账号失败:', e)
  } finally {
    loadingAccounts.value = false
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

// 计算是否所有选中项都是上架状态
const allSelectedActive = computed(() => {
  return selectedModels.value.every(m => m.status === 'active')
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
    formData.value = {
      id: model.id,
      name: model.name,
      code: model.code,
      provider: model.provider,
      category: model.category,
      version: model.version || '',
      input_price: parseFloat(model.input_price) || 0,
      output_price: parseFloat(model.output_price) || 0,
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

// 上游账号相关方法
function openAccountDialog(model) {
  currentModel.value = model
  accountDialogVisible.value = true
  loadModelAccounts(model.id)
  loadAvailableAccounts()
}

async function loadModelAccounts(modelId) {
  loadingModelAccounts.value = true
  try {
    const res = await api.get(`/models/model-upstream/model/${modelId}/`)
    modelAccounts.value = res
  } catch (e) {
    modelAccounts.value = []
  } finally {
    loadingModelAccounts.value = false
  }
}

async function loadAvailableAccounts() {
  try {
    const res = await api.get('/models/upstream-accounts/active/')
    availableAccounts.value = res
  } catch (e) {
    availableAccounts.value = []
  }
}

function openAccountForm(account = null) {
  if (account) {
    isAccountEdit.value = true
    accountFormData.value = {
      id: account.id,
      name: account.name,
      provider: account.provider,
      base_url: account.base_url,
      api_key: '',
      proxy_url: account.proxy_url || '',
      max_rpm: account.max_rpm,
      max_tpm: account.max_tpm,
      is_active: account.is_active
    }
  } else {
    isAccountEdit.value = false
    accountFormData.value = {
      id: null,
      name: '',
      provider: null,
      base_url: '',
      api_key: '',
      proxy_url: '',
      max_rpm: 60,
      max_tpm: 100000,
      is_active: true
    }
  }
  accountFormVisible.value = true
}

async function submitAccountForm() {
  try {
    await accountFormRef.value.validate()
  } catch {
    return
  }
  
  submittingAccount.value = true
  try {
    const data = { ...accountFormData.value }
    if (data.api_key === '') delete data.api_key
    
    if (isAccountEdit.value) {
      await api.patch(`/models/upstream-accounts/${data.id}/`, data)
      ElMessage.success('账号更新成功')
    } else {
      await api.post('/models/upstream-accounts/', data)
      ElMessage.success('账号添加成功')
    }
    accountFormVisible.value = false
    fetchUpstreamAccounts()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    submittingAccount.value = false
  }
}

async function testConnection(account) {
  try {
    const res = await api.post(`/models/upstream-accounts/${account.id}/test_connection/`)
    ElMessage.success('连接成功')
  } catch (e) {
    ElMessage.error(e.message || '连接失败')
  }
}

async function deleteAccount(account) {
  try {
    await ElMessageBox.confirm(`确定要删除账号 "${account.name}" 吗？`, '删除确认', { type: 'warning' })
    await api.delete(`/models/upstream-accounts/${account.id}/`)
    ElMessage.success('删除成功')
    fetchUpstreamAccounts()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function addAccountsToModel() {
  if (!selectedAccountIds.value.length) {
    ElMessage.warning('请选择账号')
    return
  }
  
  addingAccounts.value = true
  try {
    await api.post('/models/model-upstream/batch-add/', {
      model_id: currentModel.value.id,
      account_ids: selectedAccountIds.value,
      weight: newAccountWeight.value
    })
    ElMessage.success('添加成功')
    showAddAccountPanel.value = false
    selectedAccountIds.value = []
    loadModelAccounts(currentModel.value.id)
  } catch (e) {
    ElMessage.error(e.message || '添加失败')
  } finally {
    addingAccounts.value = false
  }
}

async function updateWeight(binding) {
  try {
    await api.patch(`/models/model-upstream/${binding.id}/weight/`, {
      weight: binding.weight
    })
  } catch (e) {
    ElMessage.error('更新权重失败')
  }
}

async function toggleBinding(binding) {
  try {
    await api.post(`/models/model-upstream/${binding.id}/toggle/`)
    ElMessage.success(binding.is_enabled ? '已启用' : '已禁用')
  } catch (e) {
    binding.is_enabled = !binding.is_enabled
    ElMessage.error('操作失败')
  }
}

async function removeBinding(binding) {
  try {
    await ElMessageBox.confirm('确定要移除这个账号关联吗？', '提示', { type: 'warning' })
    await api.delete('/models/model-upstream/batch-remove/', {
      data: { binding_ids: [binding.id] }
    })
    ElMessage.success('移除成功')
    loadModelAccounts(currentModel.value.id)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('移除失败')
    }
  }
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
</style>
