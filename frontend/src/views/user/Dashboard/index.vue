<template>
  <div class="dashboard">
    <!-- 头部 -->
    <div class="header">
      <div class="header-content">
        <h1>控制台</h1>
        <p class="subtitle">查看您的 API 使用概览</p>
        <!-- 余额显示 -->
        <div class="balance-display" v-loading="balanceLoading">
          <span class="balance-label">账户余额：</span>
          <span class="balance-value">¥{{ Number(balance).toFixed(4) }}</span>
          <el-button type="primary" link size="small" @click="handleRefreshBalance">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="showRecharge = true">
          <el-icon><Wallet /></el-icon>
          账户充值
        </el-button>
        <el-button type="primary" @click="$router.push('/app/api-doc')">
          <el-icon><Document /></el-icon>
          查看文档
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-grid">
      <StatCard
        :value="overview.total_requests || 0"
        label="总请求数"
        gradient="linear-gradient(135deg, #4c6ef5 0%, #748ffc 100%)"
        :icon="DataLine"
        trend="+12.5%"
        :trend-up="true"
      />
      <StatCard
        :value="overview.today_requests || 0"
        label="今日请求"
        gradient="linear-gradient(135deg, #40c057 0%, #69db7c 100%)"
        :icon="TrendCharts"
        trend="+8.2%"
        :trend-up="true"
      />
      <StatCard
        :value="`${overview.success_rate || 100}%`"
        label="成功率"
        gradient="linear-gradient(135deg, #fab005 0%, #ffd43b 100%)"
        :icon="CircleCheck"
        trend="+0.5%"
        :trend-up="true"
      />
      <StatCard
        :value="formatTokenCount(overview.total_tokens)"
        label="Token消耗"
        gradient="linear-gradient(135deg, #868e96 0%, #adb5bd 100%)"
        :icon="Coin"
        trend=""
        :trend-up="true"
      />
    </div>
    
    <!-- 热门模型区域 -->
    <div class="models-section" v-loading="loading">
      <div class="chart-card">
        <div class="chart-header">
          <h3>热门模型</h3>
          <el-button text type="primary" size="small" @click="$router.push('/app/model-square')">
            查看全部
          </el-button>
        </div>
        <div class="model-list">
          <div v-for="(model, index) in topModels" :key="model.name" class="model-item">
            <div class="model-rank" :class="{ 'top-3': index < 3 }">{{ index + 1 }}</div>
            <div class="model-info">
              <div class="model-name">{{ model.name }}</div>
              <div class="model-stats">
                <span class="model-count">{{ model.count }} 次调用</span>
                <span class="model-success-rate">成功率 {{ model.success_rate }}%</span>
              </div>
            </div>
            <div class="model-bar">
              <div class="model-bar-fill" :style="{ width: `${(model.count / (topModels[0]?.count || 1)) * 100}%` }"></div>
            </div>
          </div>
          <div v-if="topModels.length === 0" class="model-empty">
            <el-empty description="暂无数据" :image-size="60" />
          </div>
        </div>
      </div>
    </div>

    <!-- 邀请信息区域 -->
    <div class="invite-section">
      <div class="invite-card">
        <div class="invite-header">
          <div class="invite-title">
            <el-icon :size="24"><Share /></el-icon>
            <h3>邀请好友</h3>
          </div>
          <p class="invite-subtitle">邀请好友注册并充值，您可获得返利奖励</p>
        </div>
        
        <div class="invite-stats">
          <div class="invite-stat-item">
            <div class="invite-stat-value">{{ inviteInfo.invite_count }}</div>
            <div class="invite-stat-label">邀请人数</div>
          </div>
          <div class="invite-stat-item">
            <div class="invite-stat-value">¥{{ Number(inviteInfo.total_reward).toFixed(2) }}</div>
            <div class="invite-stat-label">已获取返利</div>
          </div>
          <div class="invite-stat-item">
            <div class="invite-link-box">
              <div class="invite-link-label">我的邀请链接</div>
              <div class="invite-link-url">
                <el-input v-model="inviteLink" readonly size="small" class="invite-input">
                  <template #append>
                    <el-button @click="copyInviteLink" type="primary">
                      <el-icon><DocumentCopy /></el-icon>
                      复制
                    </el-button>
                  </template>
                </el-input>
              </div>
            </div>
          </div>
        </div>
        
        <el-divider />
        
        <div class="invite-details">
          <div class="invite-rules">
            <h4>邀请规则</h4>
            <div class="rules-content">
              <p>{{ inviteInfo.config.rebate_description || '邀请好友注册并充值，您可获得返利奖励。' }}</p>
              <div class="rule-item">
                <span class="rule-label">返利方式</span>
                <span class="rule-value">{{ inviteInfo.config.rebate_type_display }}</span>
              </div>
              <div class="rule-item">
                <span class="rule-label">返利比例</span>
                <span class="rule-value">{{ (inviteInfo.config.rebate_ratio * 100).toFixed(0) }}%</span>
              </div>
              <div class="rule-item" v-if="inviteInfo.config.rebate_type === 'upgrade'">
                <span class="rule-label">升级条件</span>
                <span class="rule-value">邀请满{{ inviteInfo.config.upgrade_threshold }}人后每次充值均可获得返利</span>
              </div>
              <div class="rule-item">
                <span class="rule-label">返利阈值</span>
                <span class="rule-value">单笔返利金额达到¥{{ Number(inviteInfo.config.reward_threshold).toFixed(2) }}需管理员审核</span>
              </div>
            </div>
          </div>
          
          <div class="invite-rewards">
            <h4>收益记录（近10条）</h4>
            <div class="rewards-table">
              <el-table :data="inviteRewards" size="small" max-height="200" style="width: 100%">
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
          </div>
        </div>
      </div>
    </div>

    <!-- 充值对话框 -->
    <RechargeDialog v-model="showRecharge" @success="handleRechargeSuccess" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  DataLine, 
  TrendCharts, 
  CircleCheck, 
  Document, 
  Share, 
  DocumentCopy,
  Refresh,
  Wallet,
  Coin
} from '@element-plus/icons-vue'
import StatCard from './components/StatCard.vue'
import RechargeDialog from '@/components/RechargeDialog.vue'
import { useDashboard } from './composables/useDashboard'
import { useBilling } from '@/views/user/Billing/composables/useBilling'
import { copyToClipboard } from '@/utils/clipboard'

const {
  loading,
  overview,
  topModels,
  requestStats,
  inviteInfo,
  inviteRewards,
  loadData
} = useDashboard()

// 余额相关
const { balance, loadBalance } = useBilling()
const balanceLoading = ref(false)
const showRecharge = ref(false)

const inviteLink = computed(() => {
  const code = inviteInfo.value.invite_code
  if (!code) return ''
  return `${window.location.origin}/register?invite=${code}`
})

async function copyInviteLink() {
  if (!inviteLink.value) return
  const success = await copyToClipboard(inviteLink.value)
  if (success) {
    ElMessage.success('邀请链接已复制')
  } else {
    ElMessage.error('复制失败，请手动复制')
  }
}

// 刷新余额
async function handleRefreshBalance() {
  balanceLoading.value = true
  try {
    await loadBalance()
  } finally {
    balanceLoading.value = false
  }
}

// 充值成功回调
function handleRechargeSuccess() {
  loadBalance()
}

// 格式化Token数量
function formatTokenCount(count: number): string {
  if (count >= 1000000000) {
    return (count / 1000000000).toFixed(1) + 'B'
  }
  if (count >= 1000000) {
    return (count / 1000000).toFixed(1) + 'M'
  }
  if (count >= 1000) {
    return (count / 1000).toFixed(1) + 'K'
  }
  return count.toString()
}

onMounted(() => {
  loadData()
  loadBalance()
})
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
  animation: fadeIn 0.5s ease-out;
  min-width: 0;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-8);
}

.header-content h1 {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
  letter-spacing: -0.025em;
}

.subtitle {
  color: var(--text-secondary);
  font-size: var(--text-base);
  font-weight: var(--font-normal);
  margin-bottom: var(--space-2);
}

/* 余额显示 */
.balance-display {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: linear-gradient(135deg, var(--primary-50) 0%, var(--accent-50) 100%);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  margin-top: var(--space-3);
  width: fit-content;
}

.balance-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.balance-value {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--primary-600);
}

.header-actions {
  flex-shrink: 0;
}

/* 统计卡片网格 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-6);
  margin-bottom: var(--space-8);
}

/* 热门模型区域 */
.models-section {
  margin-bottom: var(--space-8);
}

.chart-card {
  height: 100%;
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: box-shadow var(--transition-base);
  min-width: 0;
  
  &:hover {
    box-shadow: var(--shadow-md);
  }
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--border-light);
}

.chart-header h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}

/* 模型列表 */
.model-list {
  padding: var(--space-4) var(--space-6);
}

.model-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border-light);
  
  &:last-child {
    border-bottom: none;
  }
}

.model-rank {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  background: var(--neutral-100);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  flex-shrink: 0;
  
  &.top-3 {
    background: var(--gradient-primary);
    color: var(--text-inverse);
  }
}

.model-info {
  flex: 1;
  min-width: 0;
}

.model-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin-bottom: var(--space-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-stats {
  display: flex;
  gap: var(--space-3);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.model-count {
  color: var(--text-secondary);
}

.model-success-rate {
  color: var(--success-600, #40c057);
}

.model-bar {
  width: 60px;
  height: 4px;
  background: var(--neutral-100);
  border-radius: var(--radius-full);
  overflow: hidden;
  flex-shrink: 0;
}

.model-bar-fill {
  height: 100%;
  background: var(--gradient-primary);
  border-radius: var(--radius-full);
  transition: width var(--transition-slow);
}

.model-empty {
  padding: var(--space-8) 0;
}

/* 邀请区域 */
.invite-section {
  margin-bottom: var(--space-8);
}

.invite-card {
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.invite-header {
  padding: var(--space-6);
  background: linear-gradient(135deg, var(--primary-50) 0%, var(--accent-50) 100%);
  border-bottom: 1px solid var(--border-light);
}

.invite-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
  color: var(--primary-700);
}

.invite-title h3 {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--primary-700);
  margin: 0;
}

.invite-subtitle {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  margin: 0;
}

.invite-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-6);
  padding: var(--space-6);
}

.invite-stat-item {
  text-align: center;
  padding: var(--space-4);
  background: var(--neutral-50);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
}

.invite-stat-value {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--primary-600);
  margin-bottom: var(--space-2);
  line-height: 1.2;
}

.invite-stat-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.invite-link-box {
  padding: 0;
  background: none;
  border: none;
}

.invite-link-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
  font-weight: var(--font-medium);
}

.invite-link-url {
  width: 100%;
}

.invite-input {
  width: 100%;
}

.invite-details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
  padding: var(--space-6);
}

.invite-rules h4,
.invite-rewards h4 {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-light);
}

.rules-content p {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-4);
  line-height: var(--leading-relaxed);
}

.rule-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) 0;
  border-bottom: 1px dashed var(--border-light);
  
  &:last-child {
    border-bottom: none;
  }
}

.rule-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.rule-value {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: var(--font-semibold);
  min-width: 0;
  overflow-wrap: anywhere;
}

.rewards-table {
  width: 100%;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .models-section {
    margin-bottom: var(--space-6);
  }
  
  .invite-stats {
    grid-template-columns: 1fr;
  }
  
  .invite-details {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .header {
    flex-direction: column;
    gap: var(--space-4);
  }

  .header-actions,
  .header-actions .el-button {
    width: 100%;
  }
  
  .stat-grid {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }

  .chart-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-3);
    padding: var(--space-4);
  }

  .chart-actions {
    overflow-x: auto;
  }

  .model-list,
  .invite-header,
  .invite-stats,
  .invite-details {
    padding: var(--space-4);
  }

  .invite-stats {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }

  .invite-stat-item {
    padding: var(--space-3);
  }

  .invite-stat-value {
    font-size: var(--text-2xl);
  }

  .rule-item {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-1);
  }
}

@media (max-width: 480px) {
  .invite-input :deep(.el-input-group__append) {
    padding: 0 var(--space-2);
  }

  .model-item {
    align-items: flex-start;
  }

  .model-bar {
    display: none;
  }
}
</style>
