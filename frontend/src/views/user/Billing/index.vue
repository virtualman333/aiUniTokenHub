<template>
  <div class="billing">
    <!-- 头部 -->
    <div class="header">
      <h1>账单中心</h1>
      <p class="subtitle">查看账户余额和交易记录</p>
    </div>

    <!-- 余额卡片 -->
    <el-row :gutter="24" class="balance-row">
      <el-col :span="8">
        <el-card class="balance-card">
          <div class="balance-label">账户余额</div>
          <div class="balance-value">¥{{ Number(balance).toFixed(4) }}</div>
          <el-button type="primary" class="recharge-btn" @click="showRecharge = true">
            立即充值
          </el-button>
        </el-card>
      </el-col>

      <!-- 余额续航：按最近一段时间的消耗速度估算还能用多久 -->
      <el-col :span="16">
        <el-card class="runway-card" v-loading="runwayLoading">
          <div class="runway-head">
            <span class="runway-label">余额续航</span>
            <el-tag v-if="runway" :type="runwayTagType" size="small" effect="light">
              {{ runway.level_text }}
            </el-tag>
          </div>

          <template v-if="runway">
            <div class="runway-main">
              <template v-if="runway.runway_days !== null">
                <span class="runway-days">{{ runway.runway_days }}</span>
                <span class="runway-unit">天</span>
              </template>
              <span v-else class="runway-none">{{ runway.level_text }}</span>
            </div>
            <div class="runway-advice">{{ runway.advice }}</div>
            <div v-if="runway.exhaust_date" class="runway-meta">
              预计 {{ runway.exhaust_date }} 见底 · 最近 {{ runway.window_days }} 天日均
              ¥{{ Number(runway.avg_daily_cost).toFixed(4) }}
            </div>
          </template>
          <div v-else class="runway-advice">暂时还没有可用的消耗数据</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 账单列表 -->
    <el-card v-loading="loading">
      <template #header>
        <span class="card-title">交易记录</span>
      </template>

      <el-table :data="bills">
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getTypeTag(row.type)" size="small">
              {{ getTypeText(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="120">
          <template #default="{ row }">
            <span :class="getAmountClass(row.type)">
              {{ getAmountPrefix(row.type) }}¥{{ Math.abs(Number(row.amount)).toFixed(4) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="balance" label="余额" width="120">
          <template #default="{ row }">
            ¥{{ Number(row.balance).toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" />
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadBills"
        @current-change="loadBills"
        style="margin-top: 16px; justify-content: flex-end;"
      />

    </el-card>

    <!-- 充值对话框 -->
    <RechargeDialog v-model="showRecharge" @success="handleRechargeSuccess" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { useBilling } from './composables/useBilling'
import RechargeDialog from '@/components/RechargeDialog.vue'

const {
  loading,
  balance,
  bills,
  runway,
  runwayLoading,
  pagination,
  loadBalance,
  loadBills,
  loadRunway
} = useBilling()

/** 续航分级 → 标签配色（与后端 level 字段一一对应） */
const runwayTagType = computed(() => {
  const lv = runway.value?.level
  if (lv === 'empty' || lv === 'critical') return 'danger'
  if (lv === 'watch') return 'warning'
  if (lv === 'safe') return 'success'
  return 'info'
})

const showRecharge = ref(false)

onMounted(() => {
  loadBalance()
  loadBills()
  loadRunway()
})

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

function getTypeTag(type: string) {
  const map: Record<string, any> = {
    recharge: 'success',
    consume: 'warning',
    refund: 'info',
    bonus: 'success'
  }
  return map[type] || ''
}

function getTypeText(type: string) {
  const map: Record<string, string> = {
    recharge: '充值',
    consume: '消费',
    refund: '退款',
    bonus: '赠送'
  }
  return map[type] || type
}

function getAmountPrefix(type: string) {
  return type === 'consume' ? '-' : '+'
}

function getAmountClass(type: string) {
  return type === 'consume' ? 'amount-consume' : 'amount-add'
}

// 充值成功回调
function handleRechargeSuccess() {
  loadBalance()
  loadBills()
  loadRunway()
}
</script>

<style scoped>
.billing {
  max-width: 1200px;
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
  margin-bottom: 4px;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.balance-row {
  margin-bottom: 24px;
}

.balance-card {
  background: linear-gradient(135deg, #409EFF, #66b1ff);
  color: white;
  text-align: center;
  padding: 24px;
}

.balance-label {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 8px;
}

.balance-value {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 16px;
}

.recharge-btn {
  background: white;
  color: #409EFF;
  border: none;
}

/* ---- 余额续航卡片 ---- */
.runway-card {
  height: 100%;
  padding: 20px 24px;
}

.runway-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.runway-label {
  font-size: 14px;
  color: #909399;
}

.runway-main {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 8px;
}

.runway-days {
  font-size: 36px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1;
}

.runway-unit {
  font-size: 16px;
  color: #606266;
}

.runway-none {
  font-size: 20px;
  font-weight: 600;
  color: #909399;
}

.runway-advice {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.runway-meta {
  margin-top: 8px;
  font-size: 12px;
  color: #a8abb2;
}

.card-title {
  font-weight: 600;
  font-size: 16px;
}

.amount-consume {
  color: #F56C6C;
}

.amount-add {
  color: #67C23A;
}
</style>
