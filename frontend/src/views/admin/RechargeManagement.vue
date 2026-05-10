<template>
  <div class="recharge-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="充值渠道" name="channels">
          <template #label>
            <span class="tab-label">
              <el-icon><Connection /></el-icon>
              充值渠道
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="充值套餐" name="packages">
          <template #label>
            <span class="tab-label">
              <el-icon><Goods /></el-icon>
              充值套餐
            </span>
          </template>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 充值渠道管理 -->
    <div v-if="activeTab === 'channels'" class="tab-content">
      <div class="section-header">
        <h3>充值渠道管理</h3>
        <el-button type="primary" @click="showChannelDialog('add')">
          <Plus /> 添加渠道
        </el-button>
      </div>

      <el-table :data="channels" v-loading="loadingChannels" stripe>
        <el-table-column prop="name" label="渠道名称" min-width="150">
          <template #default="{ row }">
            <div class="channel-name">
              <el-icon size="20"><Connection /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="渠道代码" width="150">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.code }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="套餐数量" width="120" align="center">
          <template #default="{ row }">
            <el-badge :value="row.package_count" :max="99" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" align="center" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" text @click="showChannelDialog('edit', row)">
              编辑
            </el-button>
            <el-button size="small" type="danger" text @click="deleteChannel(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 充值套餐管理 -->
    <div v-if="activeTab === 'packages'" class="tab-content">
      <div class="section-header">
        <h3>充值套餐管理</h3>
        <el-button type="primary" @click="showPackageDialog('add')">
          <Plus /> 添加套餐
        </el-button>
      </div>

      <!-- 渠道筛选 -->
      <el-card class="filter-card">
        <el-form inline>
          <el-form-item label="所属渠道">
            <el-select v-model="filterChannel" placeholder="全部渠道" clearable @change="loadPackages">
              <el-option
                v-for="ch in channels"
                :key="ch.id"
                :label="ch.name"
                :value="ch.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </el-card>

      <el-table :data="packages" v-loading="loadingPackages" stripe>
        <el-table-column label="所属渠道" width="120">
          <template #default="{ row }">
            <el-tag type="primary">{{ row.channel_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="充值金额" width="100" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ Number(row.amount).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="赠送金额" width="100" align="right">
          <template #default="{ row }">
            <span v-if="row.bonus > 0" class="bonus">+¥{{ Number(row.bonus).toFixed(2) }}</span>
            <span v-else class="no-bonus">-</span>
          </template>
        </el-table-column>
        <el-table-column label="实际到账" width="100" align="right">
          <template #default="{ row }">
            <span class="actual-amount">¥{{ Number(row.actual_amount).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="跳转URL" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.redirect_url" class="redirect-url">{{ row.redirect_url }}</span>
            <span v-else class="no-url">未配置</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="70" align="center" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" text @click="showPackageDialog('edit', row)">
              编辑
            </el-button>
            <el-button size="small" type="danger" text @click="deletePackage(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 渠道对话框 -->
    <el-dialog
      v-model="channelDialogVisible"
      :title="isChannelEdit ? '编辑充值渠道' : '添加充值渠道'"
      width="500px"
    >
      <el-form ref="channelFormRef" :model="channelForm" :rules="channelRules" label-width="100px">
        <el-form-item label="渠道名称" prop="name">
          <el-input v-model="channelForm.name" placeholder="例如：官方充值" />
        </el-form-item>
        <el-form-item label="渠道代码" prop="code">
          <el-input v-model="channelForm.code" placeholder="例如：official" />
          <div class="form-tip">建议使用英文，作为API标识</div>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="channelForm.description" type="textarea" :rows="2" placeholder="渠道描述" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="channelForm.icon" placeholder="图标URL或CSS类名" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="channelForm.sort_order" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="channelForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="channelDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitChannel" :loading="submittingChannel">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 套餐对话框 -->
    <el-dialog
      v-model="packageDialogVisible"
      :title="isPackageEdit ? '编辑充值套餐' : '添加充值套餐'"
      width="600px"
    >
      <el-form ref="packageFormRef" :model="packageForm" :rules="packageRules" label-width="100px">
        <el-form-item label="所属渠道" prop="channel_id">
          <el-select v-model="packageForm.channel_id" placeholder="选择渠道" style="width: 100%">
            <el-option
              v-for="ch in channels"
              :key="ch.id"
              :label="ch.name"
              :value="ch.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="充值金额" prop="amount">
          <el-input-number v-model="packageForm.amount" :min="0.01" :max="100000" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="赠送金额">
          <el-input-number v-model="packageForm.bonus" :min="0" :max="100000" :precision="2" style="width: 100%" />
          <div class="form-tip">额外赠送的金额，如充100送10</div>
        </el-form-item>
        <el-form-item label="跳转URL" prop="redirect_url">
          <el-input 
            v-model="packageForm.redirect_url" 
            type="textarea"
            :rows="2"
            placeholder="例如：https://xxx.com/pay?amount={amount}&order={order_id}"
          />
          <div class="form-tip">第三方充值网站跳转地址，支持占位符：{amount}、{bonus}、{total}、{order_id}、{user_id}、{channel_id}、{package_id}</div>
        </el-form-item>
        <el-form-item label="回调URL">
          <el-input v-model="packageForm.callback_url" placeholder="第三方回调通知地址（可选）" />
        </el-form-item>
        <el-form-item label="套餐说明">
          <el-input v-model="packageForm.description" type="textarea" :rows="2" placeholder="例如：限时优惠，充100送10" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="packageForm.sort_order" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="packageForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="packageDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPackage" :loading="submittingPackage">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Connection, Goods } from '@element-plus/icons-vue'
import api from '@/stores'

const activeTab = ref('channels')

// 渠道相关
const channels = ref<any[]>([])
const loadingChannels = ref(false)
const channelDialogVisible = ref(false)
const isChannelEdit = ref(false)
const submittingChannel = ref(false)
const channelFormRef = ref()
const editingChannelId = ref<number | null>(null)

const channelForm = reactive({
  name: '',
  code: '',
  description: '',
  icon: '',
  is_active: true,
  sort_order: 0
})

const channelRules = {
  name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入渠道代码', trigger: 'blur' }]
}

// 套餐相关
const packages = ref<any[]>([])
const loadingPackages = ref(false)
const packageDialogVisible = ref(false)
const isPackageEdit = ref(false)
const submittingPackage = ref(false)
const packageFormRef = ref()
const editingPackageId = ref<number | null>(null)
const filterChannel = ref<number | null>(null)

const packageForm = reactive({
  channel_id: null as number | null,
  amount: 100,
  bonus: 0,
  redirect_url: '',
  callback_url: '',
  description: '',
  is_active: true,
  sort_order: 0
})

const packageRules = {
  channel_id: [{ required: true, message: '请选择所属渠道', trigger: 'change' }],
  amount: [{ required: true, message: '请输入充值金额', trigger: 'blur' }],
  redirect_url: [{ required: true, message: '请输入跳转URL', trigger: 'blur' }]
}

onMounted(() => {
  loadChannels()
  loadPackages()
})

async function loadChannels() {
  loadingChannels.value = true
  try {
    const res: any = await api.get('/users/admin-recharge/list_channels/')
    channels.value = res.data || res || []
  } catch (e) {
    console.error('加载渠道失败:', e)
    channels.value = []
  } finally {
    loadingChannels.value = false
  }
}

async function loadPackages() {
  loadingPackages.value = true
  try {
    const res: any = await api.get('/users/admin-recharge/list_packages/', {
      params: filterChannel.value ? { channel_id: filterChannel.value } : {}
    })
    packages.value = res.data || res || []
  } catch (e) {
    console.error('加载套餐失败:', e)
    packages.value = []
  } finally {
    loadingPackages.value = false
  }
}

function showChannelDialog(type: 'add' | 'edit', row?: any) {
  isChannelEdit.value = type === 'edit'
  if (type === 'add') {
    editingChannelId.value = null
    Object.assign(channelForm, {
      name: '',
      code: '',
      description: '',
      icon: '',
      is_active: true,
      sort_order: 0
    })
  } else {
    editingChannelId.value = row.id
    Object.assign(channelForm, {
      name: row.name,
      code: row.code,
      description: row.description || '',
      icon: row.icon || '',
      is_active: row.is_active !== false,
      sort_order: row.sort_order || 0
    })
  }
  channelDialogVisible.value = true
}

async function submitChannel() {
  const valid = await channelFormRef.value.validate().catch(() => false)
  if (!valid) return

  submittingChannel.value = true
  try {
    if (isChannelEdit.value && editingChannelId.value) {
      await api.put(`/users/admin-recharge/update_channel/${editingChannelId.value}/`, channelForm)
      ElMessage.success('更新成功')
    } else {
      await api.post('/users/admin-recharge/create_channel/', channelForm)
      ElMessage.success('创建成功')
    }
    channelDialogVisible.value = false
    loadChannels()
  } catch (e: any) {
    ElMessage.error(e.message || (isChannelEdit.value ? '更新失败' : '创建失败'))
  } finally {
    submittingChannel.value = false
  }
}

async function deleteChannel(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定要删除渠道"${row.name}"吗？如有套餐关联则无法删除。`,
      '确认删除',
      { type: 'warning' }
    )
    await api.delete(`/users/admin-recharge/delete_channel/${row.id}/`)
    ElMessage.success('删除成功')
    loadChannels()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '删除失败')
    }
  }
}

function showPackageDialog(type: 'add' | 'edit', row?: any) {
  isPackageEdit.value = type === 'edit'
  if (type === 'add') {
    editingPackageId.value = null
    Object.assign(packageForm, {
      channel_id: null,
      amount: 100,
      bonus: 0,
      redirect_url: '',
      callback_url: '',
      description: '',
      is_active: true,
      sort_order: 0
    })
  } else {
    editingPackageId.value = row.id
    Object.assign(packageForm, {
      channel_id: row.channel,
      amount: row.amount,
      bonus: row.bonus,
      redirect_url: row.redirect_url || '',
      callback_url: row.callback_url || '',
      description: row.description || '',
      is_active: row.is_active !== false,
      sort_order: row.sort_order || 0
    })
  }
  packageDialogVisible.value = true
}

async function submitPackage() {
  const valid = await packageFormRef.value.validate().catch(() => false)
  if (!valid) return

  submittingPackage.value = true
  try {
    if (isPackageEdit.value && editingPackageId.value) {
      await api.put(`/users/admin-recharge/update_package/${editingPackageId.value}/`, packageForm)
      ElMessage.success('更新成功')
    } else {
      await api.post('/users/admin-recharge/create_package/', packageForm)
      ElMessage.success('创建成功')
    }
    packageDialogVisible.value = false
    loadPackages()
    loadChannels()
  } catch (e: any) {
    ElMessage.error(e.message || (isPackageEdit.value ? '更新失败' : '创建失败'))
  } finally {
    submittingPackage.value = false
  }
}

async function deletePackage(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定要删除此套餐吗？`,
      '确认删除',
      { type: 'warning' }
    )
    await api.delete(`/users/admin-recharge/delete_package/${row.id}/`)
    ElMessage.success('删除成功')
    loadPackages()
    loadChannels()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '删除失败')
    }
  }
}
</script>

<style scoped>
.recharge-management {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.filter-card {
  margin-bottom: 16px;
}

.channel-name {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #409EFF;
}

.amount {
  font-weight: 600;
  color: #409EFF;
  font-size: 15px;
}

.bonus {
  color: #67C23A;
  font-weight: 600;
}

.no-bonus {
  color: #909399;
}

.actual-amount {
  font-weight: 700;
  color: #E6A23C;
  font-size: 16px;
}

.redirect-url {
  color: #409EFF;
  font-size: 12px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
}

.no-url {
  color: #909399;
  font-style: italic;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
