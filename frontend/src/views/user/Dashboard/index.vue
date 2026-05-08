<template>
  <div class="dashboard">
    <!-- 头部 -->
    <div class="header">
      <div class="header-content">
        <h1>控制台</h1>
        <p class="subtitle">查看您的 API 使用概览</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="$router.push('/api-doc')">
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
        :value="`${overview.avg_response_time || 0}ms`"
        label="平均响应时间"
        gradient="linear-gradient(135deg, #868e96 0%, #adb5bd 100%)"
        :icon="Timer"
        trend="-15ms"
        :trend-up="false"
      />
    </div>

    <!-- 图表区域 -->
    <div class="charts-section" v-loading="loading">
      <div class="chart-main">
        <div class="chart-card">
          <div class="chart-header">
            <h3>请求趋势</h3>
            <div class="chart-actions">
              <el-radio-group v-model="chartPeriod" size="small">
                <el-radio-button label="week">本周</el-radio-button>
                <el-radio-button label="month">本月</el-radio-button>
                <el-radio-button label="year">全年</el-radio-button>
              </el-radio-group>
            </div>
          </div>
          <div class="chart-content">
            <RequestChart :data="requestStats" />
          </div>
        </div>
      </div>
      
      <div class="chart-side">
        <div class="chart-card">
          <div class="chart-header">
            <h3>热门API</h3>
            <el-button text type="primary" size="small">查看全部</el-button>
          </div>
          <div class="api-list">
            <div v-for="(api, index) in topAPIs" :key="api.name" class="api-item">
              <div class="api-rank" :class="{ 'top-3': index < 3 }">{{ index + 1 }}</div>
              <div class="api-info">
                <div class="api-name">{{ api.name }}</div>
                <div class="api-count">{{ api.count }} 次调用</div>
              </div>
              <div class="api-bar">
                <div class="api-bar-fill" :style="{ width: `${(api.count / (topAPIs[0]?.count || 1)) * 100}%` }"></div>
              </div>
            </div>
            <div v-if="topAPIs.length === 0" class="api-empty">
              <el-empty description="暂无数据" :image-size="60" />
            </div>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  DataLine, 
  TrendCharts, 
  CircleCheck, 
  Timer, 
  Document, 
  Share, 
  DocumentCopy 
} from '@element-plus/icons-vue'
import StatCard from './components/StatCard.vue'
import RequestChart from './components/RequestChart.vue'
import { useDashboard } from './composables/useDashboard'
import { copyToClipboard } from '@/utils/clipboard'

const {
  loading,
  overview,
  topAPIs,
  requestStats,
  inviteInfo,
  inviteRewards,
  loadData
} = useDashboard()

const chartPeriod = ref('week')

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

onMounted(() => {
  loadData()
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

/* 图表区域 */
.charts-section {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-6);
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

.chart-content {
  padding: var(--space-6);
}

/* API列表 */
.api-list {
  padding: var(--space-4) var(--space-6);
}

.api-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border-light);
  
  &:last-child {
    border-bottom: none;
  }
}

.api-rank {
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

.api-info {
  flex: 1;
  min-width: 0;
}

.api-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin-bottom: var(--space-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.api-count {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.api-bar {
  width: 60px;
  height: 4px;
  background: var(--neutral-100);
  border-radius: var(--radius-full);
  overflow: hidden;
  flex-shrink: 0;
}

.api-bar-fill {
  height: 100%;
  background: var(--gradient-primary);
  border-radius: var(--radius-full);
  transition: width var(--transition-slow);
}

.api-empty {
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
  
  .charts-section {
    grid-template-columns: 1fr;
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

  .chart-content,
  .api-list,
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

  .api-item {
    align-items: flex-start;
  }

  .api-bar {
    display: none;
  }
}
</style>
