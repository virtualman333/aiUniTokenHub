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
  pagination,
  loadBalance,
  loadBills
} = useBilling()

const showRecharge = ref(false)

onMounted(() => {
  loadBalance()
  loadBills()
})

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

function getTypeTag(type: string) {
  const map: Record<string, any> = {
    recharge: 'success',
    consume: 'warning',
    refund: 'info'
  }
  return map[type] || ''
}

function getTypeText(type: string) {
  const map: Record<string, string> = {
    recharge: '充值',
    consume: '消费',
    refund: '退款'
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
