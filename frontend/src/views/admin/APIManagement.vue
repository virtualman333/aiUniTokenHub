<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">API管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">添加API</el-button>
    </div>
    
    <el-card>
      <el-table :data="apis" v-loading="loading">
        <el-table-column prop="name" label="API名称" />
        <el-table-column prop="category_name" label="分类" width="120" />
        <el-table-column label="方法" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" min-width="200">
          <template #default="{ row }">
            <code>{{ row.path }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="rate_limit" label="限流" width="80" align="center" />
        <el-table-column prop="is_public" label="公开" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_public ? 'success' : 'warning'" size="small">
              {{ row.is_public ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center">
          <template #default="{ row }">
            <el-button size="small" @click="editAPI(row)">编辑</el-button>
            <el-button size="small" type="danger" text @click="deleteAPI(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="showCreateDialog" :title="editForm.id ? '编辑API' : '添加API'" width="600px">
      <el-form ref="formRef" :model="editForm" :rules="rules" label-width="100px">
        <el-form-item label="API名称" prop="name">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="editForm.category">
            <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="请求方法" prop="method">
          <el-select v-model="editForm.method">
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
            <el-option label="PUT" value="PUT" />
            <el-option label="DELETE" value="DELETE" />
            <el-option label="PATCH" value="PATCH" />
          </el-select>
        </el-form-item>
        <el-form-item label="路径" prop="path">
          <el-input v-model="editForm.path" placeholder="/api/v1/example" />
        </el-form-item>
        <el-form-item label="目标URL" prop="target_url">
          <el-input v-model="editForm.target_url" placeholder="https://api.example.com/v1/example" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="限流(/min)">
          <el-input-number v-model="editForm.rate_limit" :min="1" :max="10000" />
        </el-form-item>
        <el-form-item label="超时(秒)">
          <el-input-number v-model="editForm.timeout" :min="1" :max="300" />
        </el-form-item>
        <el-form-item label="公开访问">
          <el-switch v-model="editForm.is_public" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveAPI">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/stores'

const apis = ref([])
const categories = ref([])
const loading = ref(false)
const showCreateDialog = ref(false)
const formRef = ref()

const editForm = reactive({
  name: '',
  category: null,
  method: 'GET',
  path: '',
  target_url: '',
  description: '',
  rate_limit: 60,
  timeout: 30,
  is_public: true
})

const rules = {
  name: [{ required: true, message: '请输入API名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  path: [{ required: true, message: '请输入路径', trigger: 'blur' }],
  target_url: [{ required: true, message: '请输入目标URL', trigger: 'blur' }]
}

onMounted(async () => {
  await loadCategories()
  loadAPIs()
})

const loadCategories = async () => {
  categories.value = await api.get('/proxy/categories/')
}

const loadAPIs = async () => {
  loading.value = true
  try {
    const res = await api.get('/proxy/endpoints/')
    apis.value = res.results || res
  } catch (error) {
    ElMessage.error('加载API失败')
  } finally {
    loading.value = false
  }
}

const editAPI = (item) => {
  Object.assign(editForm, {
    id: item.id,
    name: item.name,
    category: item.category,
    method: item.method,
    path: item.path,
    target_url: item.target_url,
    description: item.description,
    rate_limit: item.rate_limit,
    timeout: item.timeout,
    is_public: item.is_public
  })
  showCreateDialog.value = true
}

const saveAPI = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  try {
    if (editForm.id) {
      await api.put(`/proxy/endpoints/${editForm.id}/`, editForm)
    } else {
      await api.post('/proxy/endpoints/', editForm)
    }
    ElMessage.success('保存成功')
    showCreateDialog.value = false
    loadAPIs()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const deleteAPI = async (item) => {
  try {
    await ElMessageBox.confirm(`确定要删除API "${item.name}" 吗？`, '提示', { type: 'warning' })
    await api.delete(`/proxy/endpoints/${item.id}/`)
    ElMessage.success('删除成功')
    loadAPIs()
  } catch {}
}
</script>
