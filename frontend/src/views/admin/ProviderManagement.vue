<template>
  <div class="provider-management">
    <div class="page-header">
      <h2>供应商管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="openForm()">
          <i class="icon-plus"></i> 添加供应商
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input 
        v-model="searchQuery" 
        placeholder="搜索供应商名称" 
        clearable
        @input="debounceSearch"
        style="width: 300px"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select v-model="filterStatus" placeholder="状态" clearable @change="fetchProviders">
        <el-option label="已启用" :value="true" />
        <el-option label="已禁用" :value="false" />
      </el-select>
    </div>

    <!-- 供应商列表 -->
    <el-table 
      :data="providers" 
      v-loading="loading"
      stripe
      style="width: 100%"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column prop="name" label="供应商名称" min-width="180">
        <template #default="{ row }">
          <div class="provider-cell">
            <el-avatar v-if="row.logo" :src="row.logo" :size="36" />
            <div v-else class="provider-avatar">{{ row.name?.[0]?.toUpperCase() || 'P' }}</div>
            <div class="provider-info">
              <span class="provider-name">{{ row.name }}</span>
              <span class="provider-code">{{ row.code }}</span>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="website" label="官网" width="200">
        <template #default="{ row }">
          <a v-if="row.website" :href="row.website" target="_blank" class="website-link">
            {{ row.website }}
          </a>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="model_count" label="模型数量" width="100" align="center">
        <template #default="{ row }">
          <el-tag type="info" size="small">{{ row.model_count }} 个</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '已启用' : '已禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="openForm(row)">
            编辑
          </el-button>
          <el-button size="small" link :type="row.is_active ? 'warning' : 'success'" @click="toggleStatus(row)">
            {{ row.is_active ? '禁用' : '启用' }}
          </el-button>
          <el-button size="small" link type="danger" @click="deleteProvider(row)">
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
        @size-change="fetchProviders"
        @current-change="fetchProviders"
      />
    </div>

    <!-- 表单弹窗 -->
    <el-dialog 
      v-model="formVisible" 
      :title="isEdit ? '编辑供应商' : '添加供应商'" 
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form 
        ref="formRef" 
        :model="formData" 
        :rules="formRules" 
        label-width="100px"
      >
        <el-form-item label="供应商名称" prop="name">
          <el-input v-model="formData.name" placeholder="如: OpenAI" />
        </el-form-item>
        
        <el-form-item label="供应商代码" prop="code">
          <el-input v-model="formData.code" placeholder="如: openai" :disabled="isEdit" />
          <div class="form-tip">唯一标识，用于API调用</div>
        </el-form-item>
        
        <el-form-item label="Logo URL">
          <el-input v-model="formData.logo" placeholder="https://..." />
        </el-form-item>
        
        <el-form-item label="官网">
          <el-input v-model="formData.website" placeholder="https://..." />
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input 
            v-model="formData.description" 
            type="textarea" 
            :rows="3"
            placeholder="描述供应商的特点和优势"
          />
        </el-form-item>
        
        <el-form-item label="排序">
          <el-input-number v-model="formData.order" :min="0" :max="9999" />
          <div class="form-tip">数字越小排位越靠前</div>
        </el-form-item>
        
        <el-form-item label="启用">
          <el-switch v-model="formData.is_active" />
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
import { Search } from '@element-plus/icons-vue'
import api from '@/stores'

const loading = ref(false)
const providers = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchQuery = ref('')
const filterStatus = ref('')

const formData = ref({
  id: null,
  name: '',
  code: '',
  logo: '',
  website: '',
  description: '',
  order: 0,
  is_active: true
})
const formVisible = ref(false)
const formRef = ref()
const isEdit = ref(false)
const submitting = ref(false)

const formRules = {
  name: [{ required: true, message: '请输入供应商名称', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入供应商代码', trigger: 'blur' },
    { pattern: /^[a-z0-9_-]+$/, message: '代码只能包含小写字母、数字、下划线和连字符', trigger: 'blur' }
  ]
}

let searchTimer = null

onMounted(() => {
  fetchProviders()
})

async function fetchProviders() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (searchQuery.value) params.search = searchQuery.value
    if (filterStatus.value !== '') params.is_active = filterStatus.value
    
    const res = await api.get('/models/providers/', { params })
    providers.value = res.results || res
    total.value = res.count || providers.value.length
  } catch (e) {
    ElMessage.error('获取供应商列表失败')
  } finally {
    loading.value = false
  }
}

function debounceSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    fetchProviders()
  }, 300)
}

function openForm(provider = null) {
  if (provider) {
    isEdit.value = true
    formData.value = {
      id: provider.id,
      name: provider.name,
      code: provider.code,
      logo: provider.logo || '',
      website: provider.website || '',
      description: provider.description || '',
      order: provider.order || 0,
      is_active: provider.is_active
    }
  } else {
    isEdit.value = false
    formData.value = {
      id: null,
      name: '',
      code: '',
      logo: '',
      website: '',
      description: '',
      order: 0,
      is_active: true
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
      await api.patch(`/models/providers/${data.id}/`, data)
      ElMessage.success('供应商更新成功')
    } else {
      await api.post('/models/providers/', data)
      ElMessage.success('供应商添加成功')
    }
    formVisible.value = false
    fetchProviders()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(provider) {
  try {
    const data = { is_active: !provider.is_active }
    await api.patch(`/models/providers/${provider.id}/`, data)
    ElMessage.success(provider.is_active ? '已禁用' : '已启用')
    fetchProviders()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function deleteProvider(provider) {
  try {
    await ElMessageBox.confirm(
      `确定要删除供应商 "${provider.name}" 吗？`,
      '删除确认',
      { type: 'warning' }
    )
    await api.delete(`/models/providers/${provider.id}/`)
    ElMessage.success('删除成功')
    fetchProviders()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}
</script>

<style scoped>
.provider-management {
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

.provider-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.provider-avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 16px;
}

.provider-info {
  display: flex;
  flex-direction: column;
}

.provider-name {
  font-weight: 500;
}

.provider-code {
  font-size: 12px;
  color: #909399;
}

.website-link {
  color: #409eff;
  text-decoration: none;
}

.website-link:hover {
  text-decoration: underline;
}

.text-muted {
  color: #909399;
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
  line-height: 1.2;
  margin-top: 4px;
}
</style>
