<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">用户管理</h2>
    </div>
    
    <el-card>
      <el-form inline :model="queryParams">
        <el-form-item label="用户名">
          <el-input v-model="queryParams.search" placeholder="搜索用户名" clearable @change="loadUsers" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="queryParams.role" placeholder="全部" clearable @change="loadUsers">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadUsers">搜索</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
      
      <el-table :data="users" v-loading="loading">
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="role" label="角色" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : ''" size="small">
              {{ row.role === 'admin' ? '管理员' : '用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="balance" label="余额" width="100" align="right">
          <template #default="{ row }">
            ¥{{ row.balance || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center">
          <template #default="{ row }">
            <el-button size="small" @click="editUser(row)">编辑</el-button>
            <el-button size="small" type="danger" text @click="toggleStatus(row)">
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadUsers"
        @current-change="loadUsers"
        style="margin-top: 16px; justify-content: flex-end;"
      />
    </el-card>
    
    <!-- 编辑对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑用户" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="余额">
          <el-input-number v-model="editForm.balance" :precision="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/stores'
import dayjs from 'dayjs'

const users = ref([])
const loading = ref(false)
const showEditDialog = ref(false)
const editForm = reactive({})

const queryParams = reactive({
  search: '',
  role: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

onMounted(() => {
  loadUsers()
})

const loadUsers = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (queryParams.search) params.search = queryParams.search
    if (queryParams.role) params.role = queryParams.role
    
    const res = await api.get('/users/', { params })
    users.value = res.results || res
    pagination.total = res.count || users.value.length
  } catch (error) {
    ElMessage.error('加载用户失败')
  } finally {
    loading.value = false
  }
}

const resetQuery = () => {
  queryParams.search = ''
  queryParams.role = ''
  pagination.page = 1
  loadUsers()
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

const editUser = (user) => {
  Object.assign(editForm, {
    id: user.id,
    username: user.username,
    role: user.role,
    balance: user.balance
  })
  showEditDialog.value = true
}

const saveUser = async () => {
  try {
    await api.patch(`/users/${editForm.id}/`, editForm)
    ElMessage.success('保存成功')
    showEditDialog.value = false
    loadUsers()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const toggleStatus = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要${user.is_active ? '禁用' : '启用'}用户 ${user.username} 吗？`,
      '提示'
    )
    await api.patch(`/users/${user.id}/`, { is_active: !user.is_active })
    ElMessage.success('操作成功')
    loadUsers()
  } catch {}
}
</script>
