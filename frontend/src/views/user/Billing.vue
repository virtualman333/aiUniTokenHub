<template>
  <div class="billing-container">
    <!-- 余额概览 -->
    <el-row :gutter="20" class="balance-row">
      <el-col :span="8">
        <el-card shadow="hover" class="balance-card">
          <div class="balance-item">
            <div class="balance-label">账户余额</div>
            <div class="balance-value">¥{{ userStore.balance?.toFixed(2) || '0.00' }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="balance-item">
            <div class="balance-label">本月消费</div>
            <div class="balance-value expense">¥{{ monthlyExpense.toFixed(2) }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="balance-item">
            <div class="balance-label">累计消费</div>
            <div class="balance-value expense">¥{{ totalExpense.toFixed(2) }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 充值卡片 -->
    <el-card class="recharge-card">
      <template #header>
        <div class="card-header">
          <span>账户充值</span>
        </div>
      </template>
      <div class="recharge-content">
        <div class="recharge-amounts">
          <el-radio-group v-model="selectedAmount">
            <el-radio-button :value="10">¥10</el-radio-button>
            <el-radio-button :value="50">¥50</el-radio-button>
            <el-radio-button :value="100">¥100 <span class="bonus">+5</span></el-radio-button>
            <el-radio-button :value="200">¥200 <span class="bonus">+15</span></el-radio-button>
            <el-radio-button :value="500">¥500 <span class="bonus">+50</span></el-radio-button>
          </el-radio-group>
        </div>
        <div class="custom-amount">
          <span>自定义金额：</span>
          <el-input-number v-model="customAmount" :min="1" :max="10000" />
        </div>
        <div class="payment-methods">
          <el-radio-group v-model="paymentMethod">
            <el-radio value="alipay">
              <span class="payment-icon">💙</span> 支付宝
            </el-radio>
            <el-radio value="wechat">
              <span class="payment-icon">🟢</span> 微信支付
            </el-radio>
            <el-radio value="bank">
              <span class="payment-icon">💳</span> 银行卡
            </el-radio>
          </el-radio-group>
        </div>
        <el-button type="primary" size="large" class="recharge-btn" @click="handleRecharge">
          立即充值 ¥{{ finalAmount }}
        </el-button>
      </div>
    </el-card>

    <!-- 消费记录 -->
    <el-card class="records-card">
      <template #header>
        <div class="card-header">
          <span>消费记录</span>
          <el-select v-model="timeRange" style="width: 120px">
            <el-option value="7" label="最近7天" />
            <el-option value="30" label="最近30天" />
            <el-option value="90" label="最近90天" />
          </el-select>
        </div>
      </template>
      <el-table :data="consumptionRecords" v-loading="loading">
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="endpoint_name" label="API服务" min-width="150" />
        <el-table-column prop="method" label="方法" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="response_time" label="响应时间" width="100">
          <template #default="{ row }">
            {{ row.response_time }}ms
          </template>
        </el-table-column>
        <el-table-column prop="response_status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.response_status === 200 ? 'success' : 'danger'" size="small">
              {{ row.response_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="费用" width="100">
          <template #default="{ row }">
            <span class="cost">¥{{ row.cost?.toFixed(4) || '0.00' }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="20"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadRecords"
        />
      </div>
    </el-card>

    <!-- 充值记录 -->
    <el-card class="records-card">
      <template #header>
        <span>充值记录</span>
      </template>
      <el-table :data="rechargeRecords" v-loading="rechargeLoading">
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="充值金额" width="120">
          <template #default="{ row }">
            <span class="recharge-amount">+¥{{ row.amount.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="payment_method" label="支付方式" width="120">
          <template #default="{ row }">
            {{ getPaymentLabel(row.payment_method) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
              {{ row.status === 'completed' ? '已完成' : '处理中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="order_no" label="订单号" min-width="200">
          <template #default="{ row }">
            <span class="order-no">{{ row.order_no }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores'
import api from '@/stores'

const userStore = useUserStore()

const selectedAmount = ref(100)
const customAmount = ref(0)
const paymentMethod = ref('alipay')
const timeRange = ref('30')

const loading = ref(false)
const rechargeLoading = ref(false)
const currentPage = ref(1)
const total = ref(0)

const consumptionRecords = ref([])
const rechargeRecords = ref([])

const monthlyExpense = ref(0)
const totalExpense = ref(0)

const finalAmount = computed(() => {
  if (customAmount.value > 0) return customAmount.value
  let amount = selectedAmount.value
  // 充值优惠
  if (amount === 100) amount += 5
  if (amount === 200) amount += 15
  if (amount === 500) amount += 50
  return amount
})

const loadRecords = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: 20
    }
    const res = await api.get('/users/access_logs/', { params })
    consumptionRecords.value = res.results || res || []
    total.value = res.count || 0
    
    // 计算消费
    calculateExpense()
  } catch (error) {
    console.error('加载消费记录失败:', error)
    consumptionRecords.value = []
  } finally {
    loading.value = false
  }
}

const calculateExpense = () => {
  // 简化计算，实际应该从后端获取
  monthlyExpense.value = consumptionRecords.value.reduce((sum, r) => sum + (r.cost || 0), 0) * 10
  totalExpense.value = monthlyExpense.value * 3
}

const loadRechargeRecords = async () => {
  rechargeLoading.value = true
  try {
    const res = await api.get('/users/recharges/')
    rechargeRecords.value = res.results || res || []
  } catch (error) {
    console.error('加载充值记录失败:', error)
    rechargeRecords.value = []
  } finally {
    rechargeLoading.value = false
  }
}

const handleRecharge = () => {
  ElMessage.info('充值功能开发中...')
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const getPaymentLabel = (method) => {
  const labels = { alipay: '支付宝', wechat: '微信支付', bank: '银行卡' }
  return labels[method] || method
}

onMounted(() => {
  loadRecords()
  loadRechargeRecords()
})
</script>

<style scoped>
.billing-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.balance-row {
  margin-bottom: 20px;
}

.balance-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.balance-item {
  text-align: center;
  padding: 10px;
}

.balance-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 8px;
}

.balance-value {
  font-size: 28px;
  font-weight: bold;
}

.balance-value.expense {
  color: #F56C6C;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.recharge-card {
  margin-bottom: 20px;
}

.recharge-content {
  padding: 20px 0;
}

.recharge-amounts {
  margin-bottom: 20px;
}

.recharge-amounts :deep(.el-radio-button__inner) {
  padding: 12px 24px;
  font-size: 16px;
}

.bonus {
  color: #67C23A;
  font-size: 12px;
  margin-left: 4px;
}

.custom-amount {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.payment-methods {
  margin-bottom: 30px;
}

.payment-methods :deep(.el-radio) {
  margin-right: 30px;
  font-size: 16px;
}

.payment-icon {
  margin-right: 8px;
}

.recharge-btn {
  width: 100%;
  height: 50px;
  font-size: 18px;
}

.records-card {
  margin-bottom: 20px;
}

.cost {
  color: #F56C6C;
  font-weight: 500;
}

.recharge-amount {
  color: #67C23A;
  font-weight: 500;
}

.order-no {
  font-family: monospace;
  font-size: 12px;
  color: #909399;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
