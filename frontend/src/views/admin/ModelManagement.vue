<template>
  <div class="model-management">
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
      <el-select v-model="filterStatus" placeholder="状态" clearable @change="fetchModels">
        <el-option label="已上架" value="active" />
        <el-option label="已下架" value="inactive" />
        <el-option label="测试中" value="beta" />
      </el-select>
      <el-select v-model="filterProvider" placeholder="供应商" clearable @change="fetchModels">
        <el-option 
          v-for="p in providers" 
          :key="p.id" 
          :label="p.name" 
          :value="p.id" 
        />
      </el-select>
      <el-input 
        v-model="searchQuery" 
        placeholder="搜索模型名称" 
        clearable
        @input="debounceSearch"
        style="width: 200px"
      />
    </div>

    <!-- 模型列表 -->
    <el-table 
      :data="models" 
      v-loading="loading"
      stripe
      style="width: 100%"
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
            <span>输入: ¥{{ row.input_price }}/1K</span>
            <span>输出: ¥{{ row.output_price }}/1K</span>
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
      <el-table-column label="标记" width="120">
        <template #default="{ row }">
          <el-switch 
            v-model="row.is_featured" 
            active-text="推荐"
            @change="toggleFeatured(row)"
          />
        </template>
      </el-table-column>
      <el-table-column prop="usage_count" label="调用次数" width="100" sortable />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="openModelForm(row)">
            编辑
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
        
        <el-divider>API配置</el-divider>
        
        <el-form-item label="API端点">
          <el-input v-model="formData.api_endpoint" placeholder="如: https://api.openai.com/v1" />
        </el-form-item>
        
        <el-form-item label="API模型ID">
          <el-input v-model="formData.api_model_id" placeholder="如: gpt-4-turbo-preview" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/stores'

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

const formVisible = ref(false)
const formRef = ref()
const isEdit = ref(false)
const submitting = ref(false)
const formData = ref({
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
  is_new: false,
  api_endpoint: '',
  api_model_id: ''
})

const formRules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入模型代码', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择供应商', trigger: 'change' }]
}

const commonTags = ['免费', 'GPT-4', 'Claude', 'Gemini', '国产', '开源', '大语言模型', '视觉模型']

let searchTimer = null

onMounted(() => {
  fetchModels()
  fetchProviders()
  fetchCategories()
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
    
    const res = await api.get('/models/models/', { params })
    models.value = res.results || res
    total.value = res.count || models.value.length
  } catch (e) {
    console.error('获取模型列表失败:', e)
  } finally {
    loading.value = false
  }
}

async function fetchProviders() {
  try {
    const res = await api.get('/models/providers/')
    providers.value = res
  } catch (e) {
    console.error('获取供应商失败:', e)
  }
}

async function fetchCategories() {
  try {
    const res = await api.get('/models/categories/')
    categories.value = res
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
      tags: model.tags || [],
      status: model.status,
      is_featured: model.is_featured,
      is_new: model.is_new,
      api_endpoint: model.api_endpoint || '',
      api_model_id: model.api_model_id || ''
    }
  } else {
    isEdit.value = false
    formData.value = {
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
      is_new: false,
      api_endpoint: '',
      api_model_id: ''
    }
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
      await api.put(`/models/models/${data.id}/`, data)
      ElMessage.success('模型更新成功')
    } else {
      await api.post('/models/models/', data)
      ElMessage.success('模型添加成功')
    }
    formVisible.value = false
    fetchModels()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '操作失败')
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
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.model-cell {
  display: flex;
  flex-direction: column;
}

.model-cell .model-name {
  font-weight: 500;
}

.model-cell .model-code {
  font-size: 12px;
  color: #909399;
}

.price-cell {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  color: #606266;
}

.cap-badge {
  display: inline-block;
  padding: 2px 6px;
  background: #ecf5ff;
  color: #409eff;
  border-radius: 4px;
  font-size: 11px;
  margin-right: 4px;
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
</style>
