<template>
  <div class="user-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2>用户管理</h2>
        <span class="user-count">共 {{ pagination.total }} 位用户</span>
      </div>
      <el-button type="primary" @click="openAddDialog">
        <Plus /> 添加用户
      </el-button>
    </div>

    <!-- 搜索栏 -->
    <el-card class="search-card">
      <el-form inline :model="queryParams">
        <el-form-item label="关键词">
          <el-input 
            v-model="queryParams.search" 
            placeholder="搜索用户名/邮箱/手机号" 
            clearable
            @keyup.enter="loadUsers"
          >
            <template #prefix><Search /></template>
          </el-input>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="queryParams.role" placeholder="全部" clearable>
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.is_active" placeholder="全部" clearable>
            <el-option label="正常" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadUsers">
            <Search /> 搜索
          </el-button>
          <el-button @click="resetQuery">
            <RefreshLeft /> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 用户表格 -->
    <el-card class="table-card">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="username" label="用户信息" min-width="200">
          <template #default="{ row }">
            <div class="user-cell">
              <div class="user-avatar">{{ row.username[0].toUpperCase() }}</div>
              <div class="user-detail">
                <div class="username">{{ row.username }}</div>
                <div class="email">{{ row.email || '未设置' }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="role" label="角色" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : ''" size="small" round>
              {{ row.role === 'admin' ? '管理员' : '用户' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="balance" label="余额" width="120" align="right">
          <template #default="{ row }">
            <span class="balance">¥{{ Number(row.balance || 0).toFixed(4) }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="is_active" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small" effect="light">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="company" label="公司" width="150" show-overflow-tooltip />
        
        <el-table-column prop="created_at" label="注册时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="editUser(row)">
              编辑
            </el-button>
            <el-button size="small" type="warning" link @click="adjustBalance(row)">
              调余额
            </el-button>
            <el-button 
              size="small" 
              :type="row.is_active ? 'danger' : 'success'" 
              link 
              @click="toggleStatus(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @change="loadUsers"
        />
      </div>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑用户" width="500px" destroy-on-close>
      <el-form ref="editFormRef" :model="editForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="editForm.phone" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="editForm.company" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- 调整余额对话框 -->
    <el-dialog v-model="showBalanceDialog" title="调整余额" width="500px">
      <el-form label-width="100px">
        <el-form-item label="用户名">
          <span>{{ currentUser?.username }}</span>
        </el-form-item>
        <el-form-item label="当前余额">
          <span class="balance">¥{{ Number(currentUser?.balance || 0).toFixed(6) }}</span>
        </el-form-item>
        <el-form-item label="调整方式">
          <el-radio-group v-model="balanceMode">
            <el-radio value="add">增减金额</el-radio>
            <el-radio value="set">直接设置</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="balanceMode === 'add' ? '调整金额' : '设置金额'">
          <el-input-number 
            v-model="balanceAmount" 
            :precision="6" 
            :step="1" 
            :min="-999999" 
            :max="999999"
            style="width: 200px"
          />
          <div class="quick-options" style="margin-left: 10px">
            <el-button-group>
              <el-button size="small" @click="balanceAmount = 0">清零</el-button>
              <el-button size="small" @click="setBalanceTo(0.01)">设为0.01</el-button>
              <el-button size="small" @click="setBalanceTo(1)">设为1</el-button>
              <el-button size="small" @click="setBalanceTo(10)">设为10</el-button>
            </el-button-group>
          </div>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="balanceNote" placeholder="调整原因（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBalanceDialog = false">取消</el-button>
        <el-button type="primary" @click="saveBalance">确认调整</el-button>
      </template>
    </el-dialog>

    <!-- 添加用户对话框 -->
    <el-dialog v-model="showAddDialog" title="添加用户" width="500px" destroy-on-close>
      <el-form ref="addFormRef" :model="addForm" :rules="addFormRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="addForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="addForm.password" type="password" placeholder="请输入密码（至少6位）" show-password />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="addForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="addForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="addForm.company" placeholder="请输入公司名称" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="addForm.role" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAddUser">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, RefreshLeft, Plus } from '@element-plus/icons-vue'
import api from '@/stores'
import dayjs from 'dayjs'

const users = ref([])
const loading = ref(false)
const showEditDialog = ref(false)
const showAddDialog = ref(false)
const showBalanceDialog = ref(false)
const currentUser = ref(null)
const balanceAmount = ref(0)
const balanceNote = ref('')
const balanceMode = ref('add')  // 'add' 或 'set'
const editFormRef = ref()
const addFormRef = ref()

// 设置余额的快捷方法
const setBalanceTo = (value) => {
  balanceMode.value = 'set'
  balanceAmount.value = value
}

const queryParams = reactive({
  search: '',
  role: '',
  is_active: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const defaultEditForm = () => ({
  id: null,
  username: '',
  email: '',
  phone: '',
  company: '',
  role: 'user'
})

const editForm = ref({ ...defaultEditForm() })

const defaultAddForm = () => ({
  username: '',
  email: '',
  phone: '',
  company: '',
  password: '',
  role: 'user'
})

const addForm = ref({ ...defaultAddForm() })

const addFormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码至少6位', trigger: 'blur' }]
}

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
    if (queryParams.is_active !== '') params.is_active = queryParams.is_active
    
    const res = await api.get('/dashboard/admin/users/', { params })
    users.value = res.results || res
    pagination.total = res.total || res.count || users.value.length
  } catch (error) {
    ElMessage.error('加载用户失败: ' + (error.message || ''))
  } finally {
    loading.value = false
  }
}

const resetQuery = () => {
  queryParams.search = ''
  queryParams.role = ''
  queryParams.is_active = ''
  pagination.page = 1
  loadUsers()
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

const editUser = (user) => {
  editForm.value = {
    id: user.id,
    username: user.username,
    email: user.email,
    phone: user.phone,
    company: user.company,
    role: user.role
  }
  showEditDialog.value = true
}

const saveUser = async () => {
  try {
    await api.patch(`/dashboard/admin/users/${editForm.value.id}/`, {
      email: editForm.value.email,
      phone: editForm.value.phone,
      company: editForm.value.company,
      role: editForm.value.role
    })
    ElMessage.success('保存成功')
    showEditDialog.value = false
    loadUsers()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const adjustBalance = (user) => {
  currentUser.value = user
  balanceAmount.value = 0
  balanceNote.value = ''
  showBalanceDialog.value = true
}

const saveBalance = async () => {
  try {
    const data = await api.patch(`/dashboard/admin/users/${currentUser.value.id}/balance/`, {
      amount: balanceAmount.value,
      note: balanceNote.value,
      set_balance: balanceMode.value === 'set'
    })
    ElMessage.success(data?.message || '余额调整成功')
    showBalanceDialog.value = false
    loadUsers()
  } catch (error) {
    ElMessage.error('调整失败: ' + (error.response?.data?.detail || error.message || ''))
  }
}

const toggleStatus = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要${user.is_active ? '禁用' : '启用'}用户 ${user.username} 吗？`,
      '提示'
    )
    await api.post(`/dashboard/admin/users/${user.id}/toggle-status/`)
    ElMessage.success('操作成功')
    loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '操作失败')
    }
  }
}

const resetAddForm = () => {
  addForm.value = { ...defaultAddForm() }
}

const openAddDialog = () => {
  resetAddForm()
  showAddDialog.value = true
}

const handleAddUser = async () => {
  try {
    await addFormRef.value.validate()
    await api.post('/users/auth/register/', {
      username: addForm.value.username,
      password: addForm.value.password,
      email: addForm.value.email,
      phone: addForm.value.phone,
      company: addForm.value.company,
      role: addForm.value.role
    })
    ElMessage.success('添加用户成功')
    showAddDialog.value = false
    loadUsers()
  } catch (error) {
    ElMessage.error(error.message || '添加用户失败')
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

.user-count {
  font-size: 14px;
  color: #6b7280;
}

.search-card {
  margin-bottom: 20px;
  border-radius: 12px;
}

.table-card {
  border-radius: 12px;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 16px;
}

.user-detail .username {
  font-weight: 500;
  color: #1f2937;
}

.user-detail .email {
  font-size: 12px;
  color: #6b7280;
}

.balance {
  font-weight: 600;
  color: #f59e0b;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
