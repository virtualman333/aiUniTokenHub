<template>
  <div class="invite-management">
    <div class="header">
      <h1>邀请返利管理</h1>
      <p class="subtitle">配置返利规则和审核返利申请</p>
    </div>

    <el-row :gutter="24">
      <!-- 返利配置 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span class="card-title">返利配置</span>
          </template>
          <el-form :model="config" label-width="120px">
            <el-form-item label="返利方式">
              <el-select v-model="config.rebate_type" style="width: 100%;">
                <el-option label="首次返利" value="first" />
                <el-option label="每次返利" value="every" />
                <el-option label="满X人升级为每次返利" value="upgrade" />
              </el-select>
            </el-form-item>
            <el-form-item label="返利比例">
              <el-input-number v-model="config.rebate_ratio" :min="0" :max="1" :step="0.01" :precision="2" />
              <span style="margin-left: 8px;">{{ (config.rebate_ratio * 100).toFixed(0) }}%</span>
            </el-form-item>
            <el-form-item label="升级所需人数" v-if="config.rebate_type === 'upgrade'">
              <el-input-number v-model="config.upgrade_threshold" :min="1" :max="1000" />
            </el-form-item>
            <el-form-item label="返利审核阈值">
              <el-input-number v-model="config.reward_threshold" :min="0" :max="10000" :step="10" :precision="2" />
              <span style="margin-left: 8px;">元</span>
              <div class="form-tip">单笔返利金额达到此值需管理员审核</div>
            </el-form-item>
            <el-form-item label="返利说明">
              <el-input v-model="config.rebate_description" type="textarea" :rows="4" placeholder="输入返利说明文案" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 返利审核 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span class="card-title">返利审核</span>
              <el-tag type="warning">待审核：{{ pendingCount }}</el-tag>
            </div>
          </template>
          <el-table :data="rewards" v-loading="loading" max-height="500">
            <el-table-column prop="inviter_username" label="邀请人" width="100" />
            <el-table-column prop="invitee_username" label="被邀请人" width="100" />
            <el-table-column label="充值金额" width="100">
              <template #default="{ row }">¥{{ Number(row.recharge_amount).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="返利金额" width="100">
              <template #default="{ row }">¥{{ Number(row.reward_amount).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'pending' ? 'warning' : 'danger'" size="small">
                  {{ row.status_display }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <template v-if="row.status === 'pending'">
                  <el-button type="success" size="small" @click="handleApprove(row.id)">通过</el-button>
                  <el-button type="danger" size="small" @click="handleReject(row.id)">拒绝</el-button>
                </template>
                <span v-else class="reviewed-time">{{ formatDate(row.reviewed_at) }}</span>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :total="pagination.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @size-change="loadRewards"
            @current-change="loadRewards"
            style="margin-top: 16px; justify-content: flex-end;"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import api from '@/stores'

const loading = ref(false)
const saving = ref(false)
const config = reactive({
  rebate_type: 'first',
  rebate_ratio: 0.1,
  upgrade_threshold: 10,
  reward_threshold: 100,
  rebate_description: ''
})
const rewards = ref([])
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const pendingCount = computed(() => rewards.value.filter((r: any) => r.status === 'pending').length)

function formatDate(date: string) {
  return date ? dayjs(date).format('MM-DD HH:mm') : '-'
}

async function loadConfig() {
  try {
    const res = await api.get('/dashboard/admin/invite/config/')
    Object.assign(config, res)
  } catch (e) {
    console.error('获取配置失败:', e)
  }
}

async function saveConfig() {
  saving.value = true
  try {
    await api.put('/dashboard/admin/invite/config/', config)
    ElMessage.success('配置已保存')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function loadRewards() {
  loading.value = true
  try {
    const res: any= await api.get('/dashboard/admin/invite/rewards/', {
      params: {
        page: pagination.page,
        page_size: pagination.pageSize
      }
    })
    rewards.value = res.results || res.data || []
    pagination.total = res.total || 0
  } catch (e) {
    console.error('获取返利记录失败:', e)
  } finally {
    loading.value = false
  }
}

async function handleApprove(id: number) {
  try {
    await ElMessageBox.confirm('确认通过此返利申请？', '审核确认', { type: 'warning' })
    await api.post(`/dashboard/admin/invite/rewards/${id}/approve/`)
    ElMessage.success('审核通过')
    loadRewards()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '操作失败')
    }
  }
}

async function handleReject(id: number) {
  try {
    await ElMessageBox.confirm('确认拒绝此返利申请？', '审核确认', { type: 'warning' })
    await api.post(`/dashboard/admin/invite/rewards/${id}/reject/`)
    ElMessage.success('已拒绝')
    loadRewards()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '操作失败')
    }
  }
}

onMounted(() => {
  loadConfig()
  loadRewards()
})
</script>

<style scoped>
.invite-management {
  padding: 0;
}

.header {
  margin-bottom: 24px;
}

.header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.subtitle {
  color: #6b7280;
  font-size: 14px;
}

.card-title {
  font-weight: 600;
  font-size: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.reviewed-time {
  font-size: 12px;
  color: #909399;
}
</style>