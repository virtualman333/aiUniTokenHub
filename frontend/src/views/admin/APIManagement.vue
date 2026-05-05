<template>
  <div class="api-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2>API管理</h2>
        <span class="api-count">共 {{ endpoints.length }} 个API</span>
      </div>
      <el-button type="primary" @click="openDialog()">
        <Plus /> 添加API
      </el-button>
    </div>

    <!-- API表格 -->
    <el-card class="table-card">
      <el-table :data="endpoints" v-loading="loading" stripe>
        <el-table-column prop="name" label="API名称" min-width="180">
          <template #default="{ row }">
            <div class="api-name">
              <span class="name">{{ row.name }}</span>
              <span class="desc">{{ row.description }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.category_name || getCategoryName(row.category) }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="method" label="方法" width="80" align="center">
          <template #default="{ row }">
            <el-tag 
              size="small" 
              :type="getMethodType(row.method)"
              effect="dark"
            >
              {{ row.method }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="path" label="路径" min-width="220">
          <template #default="{ row }">
            <code class="path-code">{{ row.path }}</code>
          </template>
        </el-table-column>
        
        <el-table-column prop="rate_limit" label="限流" width="80" align="center">
          <template #default="{ row }">
            <span class="rate-limit">{{ row.rate_limit }}/min</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="price" label="价格" width="100" align="right">
          <template #default="{ row }">
            <span class="price">¥{{ (row.price || 0).toFixed(4) }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="is_public" label="公开" width="80" align="center">
          <template #default="{ row }">
            <el-switch 
              :model-value="row.is_public" 
              @change="togglePublic(row)"
            />
          </template>
        </el-table-column>
        
        <el-table-column prop="is_active" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openDialog(row)">
              编辑
            </el-button>
            <el-button size="small" type="danger" link @click="deleteEndpoint(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog 
      v-model="showDialog" 
      :title="editForm.id ? '编辑API' : '添加API'" 
      width="650px" 
      destroy-on-close
    >
      <el-form ref="formRef" :model="editForm" :rules="rules" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="API名称" prop="name">
              <el-input v-model="editForm.name" placeholder="ChatGPT-4o" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类" prop="category">
              <el-select v-model="editForm.category" placeholder="请选择" style="width: 100%">
                <el-option 
                  v-for="cat in categories" 
                  :key="cat.id" 
                  :label="cat.name" 
                  :value="cat.id" 
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="请求方法" prop="method">
              <el-select v-model="editForm.method" style="width: 100%">
                <el-option label="GET" value="GET" />
                <el-option label="POST" value="POST" />
                <el-option label="PUT" value="PUT" />
                <el-option label="DELETE" value="DELETE" />
                <el-option label="PATCH" value="PATCH" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="价格(元)" prop="price">
              <el-input-number 
                v-model="editForm.price" 
                :precision="6" 
                :min="0" 
                :step="0.0001"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="路径" prop="path">
          <el-input v-model="editForm.path" placeholder="/v1/chat/completions" />
        </el-form-item>
        
        <el-form-item label="目标URL" prop="target_url">
          <el-input 
            v-model="editForm.target_url" 
            placeholder="https://api.openai.com/v1/chat/completions"
          />
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input 
            v-model="editForm.description" 
            type="textarea" 
            :rows="2"
            placeholder="API功能描述"
          />
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="限流(次/分)">
              <el-input-number v-model="editForm.rate_limit" :min="1" :max="10000" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="超时(秒)">
              <el-input-number v-model="editForm.timeout" :min="1" :max="300" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="公开访问">
              <el-switch v-model="editForm.is_public" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用状态">
              <el-switch v-model="editForm.is_active" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveEndpoint">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/stores'

const endpoints = ref([])
const categories = ref([])
const loading = ref(false)
const showDialog = ref(false)
const formRef = ref()

const defaultEditForm = () => ({
  id: null,
  name: '',
  category: null,
  method: 'POST',
  path: '',
  target_url: '',
  description: '',
  rate_limit: 60,
  timeout: 30,
  price: 0,
  is_public: true,
  is_active: true
})

const editForm = ref({ ...defaultEditForm() })

const rules = {
  name: [{ required: true, message: '请输入API名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  path: [{ required: true, message: '请输入路径', trigger: 'blur' }],
  target_url: [{ required: true, message: '请输入目标URL', trigger: 'blur' }]
}

onMounted(async () => {
  await Promise.all([loadCategories(), loadEndpoints()])
})

const loadCategories = async () => {
  try {
    categories.value = await api.get('/proxy/categories/')
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

const loadEndpoints = async () => {
  loading.value = true
  try {
    const res = await api.get('/proxy/endpoints/')
    endpoints.value = res.results || res
  } catch (error) {
    ElMessage.error('加载API失败')
  } finally {
    loading.value = false
  }
}

const getCategoryName = (categoryId) => {
  const cat = categories.value.find(c => c.id === categoryId)
  return cat?.name || '未分类'
}

const getMethodType = (method) => {
  const types = {
    GET: '',
    POST: 'success',
    PUT: 'warning',
    DELETE: 'danger',
    PATCH: 'info'
  }
  return types[method] || ''
}

const openDialog = (row = null) => {
  if (row) {
    editForm.value = {
      id: row.id,
      name: row.name,
      category: row.category,
      method: row.method,
      path: row.path,
      target_url: row.target_url,
      description: row.description,
      rate_limit: row.rate_limit,
      timeout: row.timeout,
      price: row.price,
      is_public: row.is_public,
      is_active: row.is_active
    }
  } else {
    editForm.value = {
      ...defaultEditForm(),
      category: categories.value[0]?.id || null
    }
  }
  showDialog.value = true
}

const saveEndpoint = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  
  try {
    if (editForm.value.id) {
      await api.put(`/proxy/endpoints/${editForm.value.id}/`, editForm.value)
    } else {
      await api.post('/proxy/endpoints/', editForm.value)
    }
    ElMessage.success('保存成功')
    showDialog.value = false
    loadEndpoints()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const deleteEndpoint = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除API "${row.name}" 吗？`, '提示', { type: 'warning' })
    await api.delete(`/proxy/endpoints/${row.id}/`)
    ElMessage.success('删除成功')
    loadEndpoints()
  } catch {}
}

const togglePublic = async (row) => {
  try {
    await api.patch(`/proxy/endpoints/${row.id}/`, { is_public: !row.is_public })
    row.is_public = !row.is_public
  } catch {
    ElMessage.error('修改失败')
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.api-count {
  font-size: 14px;
  color: #6b7280;
}

.table-card {
  border-radius: 12px;
}

.api-name {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.api-name .name {
  font-weight: 500;
  color: #1f2937;
}

.api-name .desc {
  font-size: 12px;
  color: #6b7280;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.path-code {
  font-size: 12px;
  background: #f3f4f6;
  padding: 4px 8px;
  border-radius: 4px;
  color: #4f46e5;
}

.rate-limit {
  font-size: 12px;
  color: #6b7280;
}

.price {
  font-weight: 600;
  color: #f59e0b;
}
</style>
