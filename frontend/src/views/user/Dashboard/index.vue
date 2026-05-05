<template>
  <div class="dashboard">
    <!-- 头部 -->
    <div class="header">
      <h1>控制台</h1>
      <p class="subtitle">查看您的 API 使用概览</p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <StatCard
          :value="overview.total_requests || 0"
          label="总请求数"
          gradient="linear-gradient(135deg, #409EFF, #66b1ff)"
        />
      </el-col>
      <el-col :span="6">
        <StatCard
          :value="overview.today_requests || 0"
          label="今日请求"
          gradient="linear-gradient(135deg, #67C23A, #85ce61)"
        />
      </el-col>
      <el-col :span="6">
        <StatCard
          :value="`${overview.success_rate || 100}%`"
          label="成功率"
          gradient="linear-gradient(135deg, #E6A23C, #ebb563)"
        />
      </el-col>
      <el-col :span="6">
        <StatCard
          :value="`${overview.avg_response_time || 0}ms`"
          label="平均响应时间"
          gradient="linear-gradient(135deg, #909399, #a6a9ad)"
        />
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" v-loading="loading">
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <span class="card-title">请求趋势</span>
          </template>
          <RequestChart :data="requestStats" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <span class="card-title">热门API</span>
          </template>
          <el-table :data="topAPIs" size="small">
            <el-table-column prop="name" label="API名称" />
            <el-table-column prop="count" label="调用次数" width="100" align="right" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 邀请信息区域 -->
    <el-card class="invite-card" style="margin-top: 24px;">
      <template #header>
        <span class="card-title">邀请好友</span>
      </template>
      <el-row :gutter="24">
        <el-col :span="8">
          <div class="invite-stat">
            <div class="invite-stat-value">{{ inviteInfo.invite_count }}</div>
            <div class="invite-stat-label">邀请人数</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="invite-stat">
            <div class="invite-stat-value">¥{{ Number(inviteInfo.total_reward).toFixed(2) }}</div>
            <div class="invite-stat-label">已获取返利</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="invite-link-box">
            <div class="invite-link-label">我的邀请链接</div>
            <div class="invite-link-url">
              <el-input v-model="inviteLink" readonly size="small">
                <template #append>
                  <el-button @click="copyInviteLink">复制</el-button>
                </template>
              </el-input>
            </div>
          </div>
        </el-col>
      </el-row>
      <el-divider />
      <el-row :gutter="24">
        <el-col :span="12">
          <div class="invite-rules">
            <h4>邀请规则</h4>
            <p>{{ inviteInfo.config.rebate_description || '邀请好友注册并充值，您可获得返利奖励。' }}</p>
            <p>返利方式：{{ inviteInfo.config.rebate_type_display }}</p>
            <p>返利比例：{{ (inviteInfo.config.rebate_ratio * 100).toFixed(0) }}%</p>
            <p v-if="inviteInfo.config.rebate_type === 'upgrade'">
              升级条件：邀请满{{ inviteInfo.config.upgrade_threshold }}人后每次充值均可获得返利
            </p>
            <p>返利阈值：单笔返利金额达到¥{{ Number(inviteInfo.config.reward_threshold).toFixed(2) }}需管理员审核</p>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="invite-rewards">
            <h4>收益记录（近10条）</h4>
            <el-table :data="inviteRewards" size="small" max-height="200">
              <el-table-column prop="invitee_username" label="被邀请人" />
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
            </el-table>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import StatCard from './components/StatCard.vue'
import RequestChart from './components/RequestChart.vue'
import { useDashboard } from './composables/useDashboard'

const {
  loading,
  overview,
  topAPIs,
  requestStats,
  inviteInfo,
  inviteRewards,
  loadData
} = useDashboard()

const inviteLink = computed(() => {
  const code = inviteInfo.value.invite_code
  if (!code) return ''
  return `${window.location.origin}/register?invite=${code}`
})

function copyInviteLink() {
  if (!inviteLink.value) return
  navigator.clipboard.writeText(inviteLink.value).then(() => {
    ElMessage.success('邀请链接已复制')
  }).catch(() => {
    ElMessage.error('复制失败，请手动复制')
  })
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
  font-size: 16px;
}

.stat-row {
  margin-bottom: 24px;
}

.chart-card {
  height: 100%;
}

.card-title {
  font-weight: 600;
  font-size: 16px;
}

.invite-card {
  margin-top: 24px;
}

.invite-stat {
  text-align: center;
  padding: 16px 0;
}

.invite-stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #409EFF;
  margin-bottom: 8px;
}

.invite-stat-label {
  font-size: 14px;
  color: #666;
}

.invite-link-box {
  padding: 16px 0;
}

.invite-link-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.invite-rules h4,
.invite-rewards h4 {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.invite-rules p {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
  line-height: 1.6;
}
</style>
