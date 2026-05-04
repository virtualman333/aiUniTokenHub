<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">API分类</h2>
      <el-button type="primary" @click="showDialog = true">添加分类</el-button>
    </div>
    
    <el-card>
      <el-table :data="categories" v-loading="loading">
        <el-table-column prop="name" label="分类名称" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="order" label="排序" width="80" align="center" />
        <el-table-column prop="endpoint_count" label="API数量" width="100" align="center" />
        <el-table-column prop="is_active" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button size="small" @click="editCategory(row)">编辑</el-button>
            <el-button size="small" type="danger" text @click="deleteCategory(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <el-dialog v-model="showDialog" :title="editForm.id ? '编辑分类' : '添加分类'" width="500px">
      <el-form :model="editForm" :rules="rules" label-width="100px">
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="editForm.order" :min="0" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="editForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveCategory">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/stores'

const categories = ref([])
const loading = ref(false)
const showDialog = ref(false)

const editForm = reactive({
  id: null,
  name: '',
  description: '',
  order: 0,
  is_active: true
})

const rules = {
  name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }]
}

onMounted(() => {
  loadCategories()
})

const loadCategories = async () => {
  loading.value = true
  try {
    categories.value = await api.get('/proxy/categories/')
  } catch (error) {
    ElMessage.error('加载分类失败')
  } finally {
    loading.value = false
  }
}

const editCategory = (cat) => {
  Object.assign(editForm, cat)
  showDialog.value = true
}

const saveCategory = async () => {
  try {
    if (editForm.id) {
      await api.put(`/proxy/categories/${editForm.id}/`, editForm)
    } else {
      await api.post('/proxy/categories/', editForm)
    }
    ElMessage.success('保存成功')
    showDialog.value = false
    loadCategories()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const deleteCategory = async (cat) => {
  try {
    await ElMessageBox.confirm(`确定要删除分类 "${cat.name}" 吗？`, '提示', { type: 'warning' })
    await api.delete(`/proxy/categories/${cat.id}/`)
    ElMessage.success('删除成功')
    loadCategories()
  } catch {}
}
</script>
