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
    <el-dialog v-model="showRecharge" title="账户充值" width="700px">
      <el-tabs v-model="payMethod" @tab-change="handlePayMethodChange">
        <el-tab-pane label="卡密充值" name="card">
          <el-form label-width="80px" style="margin-top: 16px;">
            <el-form-item label="卡密码">
              <el-input v-model="cardCode" placeholder="请输入卡密码" clearable />
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="套餐充值" name="package" v-if="rechargeChannels.length > 0">
          <div class="package-content">
            <div class="channel-selector">
              <span class="label">选择充值渠道：</span>
              <el-radio-group v-model="selectedChannel" @change="handleChannelChange">
                <el-radio-button
                  v-for="ch in rechargeChannels"
                  :key="ch.id"
                  :value="ch.id"
                >
                  {{ ch.name }}
                </el-radio-button>
              </el-radio-group>
            </div>

            <div v-if="selectedChannelPackages.length > 0" class="package-grid">
              <div
                v-for="pkg in selectedChannelPackages"
                :key="pkg.id"
                class="package-item"
                :class="{ active: selectedPackage === pkg.id }"
                @click="selectedPackage = pkg.id"
              >
                <div class="package-amount">
                  <span class="symbol">¥</span>
                  <span class="value">{{ Number(pkg.amount).toFixed(0) }}</span>
                </div>
                <div v-if="pkg.bonus > 0" class="package-bonus">
                  送 ¥{{ Number(pkg.bonus).toFixed(0) }}
                </div>
                <div class="package-actual">
                  到账 ¥{{ Number(pkg.actual_amount).toFixed(2) }}
                </div>
                <div v-if="pkg.description" class="package-desc">
                  {{ pkg.description }}
                </div>
              </div>
            </div>

            <div v-else-if="selectedChannel && loadingPackages" class="loading-packages">
              <el-icon class="is-loading"><Loading /></el-icon>
              加载套餐中...
            </div>

            <div v-else-if="selectedChannel" class="no-packages">
              暂无套餐，请选择其他渠道或联系管理员
            </div>

            <div v-if="!selectedChannel && rechargeChannels.length > 0" class="select-channel-tip">
              请先选择一个充值渠道
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="showRecharge = false">取消</el-button>
        <el-button
          v-if="payMethod === 'card'"
          type="primary"
          :loading="recharging"
          @click="handleRedeemCard"
        >
          确认兑换
        </el-button>
        <el-button
          v-if="payMethod === 'package'"
          type="primary"
          :loading="recharging"
          :disabled="!canSubmitPackage"
          @click="handlePackageRecharge"
        >
          立即充值
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { useBilling } from './composables/useBilling'
import { fireConfetti } from '@/utils/confetti'
import api from '@/stores'

const {
  loading,
  balance,
  bills,
  pagination,
  loadBalance,
  loadBills,
  redeemCard
} = useBilling()

const showRecharge = ref(false)
const recharging = ref(false)
const payMethod = ref('card')
const cardCode = ref('')

// 充值渠道相关
const rechargeChannels = ref<any[]>([])
const selectedChannel = ref<number | null>(null)
const channelPackages = ref<any[]>([])
const loadingPackages = ref(false)
const selectedPackage = ref<number | null>(null)

onMounted(() => {
  loadBalance()
  loadBills()
  loadRechargeChannels()
})

async function loadRechargeChannels() {
  try {
    const res: any = await api.get('/users/recharge/channels/')
    rechargeChannels.value = res.data || res || []
  } catch (e) {
    console.error('加载充值渠道失败:', e)
    rechargeChannels.value = []
  }
}

async function loadChannelPackages(channelId: number) {
  loadingPackages.value = true
  try {
    const res: any = await api.get('/users/recharge/packages/', {
      params: { channel_id: channelId }
    })
    channelPackages.value = res.data || res || []
    selectedPackage.value = null
  } catch (e) {
    console.error('加载套餐失败:', e)
    channelPackages.value = []
  } finally {
    loadingPackages.value = false
  }
}

function handleChannelChange(channelId: number) {
  selectedPackage.value = null
  if (channelId) {
    loadChannelPackages(channelId)
  }
}

const selectedChannelPackages = computed(() => {
  return channelPackages.value.filter(pkg => pkg.is_active)
})

const canSubmitPackage = computed(() => {
  return selectedPackage.value !== null && payMethod.value === 'package'
})

async function handlePackageRecharge() {
  if (!selectedPackage.value) {
    ElMessage.warning('请选择充值套餐')
    return
  }

  recharging.value = true
  try {
    const res: any = await api.post('/users/recharge/submit/', {
      package_id: selectedPackage.value,
      channel_id: selectedChannel.value
    })
    
    // 第三方充值流程
    if (res.redirect_url) {
      // 打开第三方充值页面
      window.open(res.redirect_url, '_blank')
      
      // 提示用户
      ElMessageBox.confirm(
        `即将跳转到【${res.channel_name}】进行支付。\n\n请在第三方网站完成支付后，返回本页输入卡密完成充值。\n\n套餐：${res.package_name}\n充值金额：¥${res.amount} + 赠送 ¥${res.bonus}\n总计到账：¥${res.total}`,
        '即将跳转到第三方充值',
        {
          confirmButtonText: '已支付，返回输入卡密',
          cancelButtonText: '去支付',
          type: 'info',
          center: true
        }
      ).then(() => {
        // 用户点击"已支付"，切换到卡密充值
        payMethod.value = 'card'
        showRecharge.value = true
      }).catch(() => {
        // 用户点击"去支付"，什么都不做，保持当前页面
      })
      
      // 关闭对话框
      showRecharge.value = false
      return
    }
    
    // 如果没有返回redirect_url（兼容旧逻辑）
    ElMessage.success(res.message || '充值成功')
    showRecharge.value = false
    selectedPackage.value = null
    loadBalance()
    loadBills()
    fireConfetti()
  } catch (e: any) {
    const errorMsg = e.response?.data?.msg || e.response?.data?.message || e.message || '充值失败'
    ElMessage.error(errorMsg)
  } finally {
    recharging.value = false
  }
}

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

async function handleRedeemCard() {
  if (!cardCode.value.trim()) {
    ElMessage.warning('请输入卡密码')
    return
  }
  recharging.value = true
  try {
    const res = await redeemCard(cardCode.value.trim())
    ElMessage.success(`卡密兑换成功，充值 ¥${res.card_amount}`)
    showRecharge.value = false
    cardCode.value = ''
    loadBalance()
    loadBills()
    
    // 触发彩色纸屑礼花筒效果
    fireConfetti()
  } catch (e: any) {
    const errorMsg = e.response?.data?.msg || e.response?.data?.detail || e.message || '卡密兑换失败'
    ElMessage.error(errorMsg)
  } finally {
    recharging.value = false
  }
}

function handlePayMethodChange() {
  cardCode.value = ''
  selectedPackage.value = null
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

.coming-soon {
  text-align: center;
  padding: 40px 0;
  color: #909399;
  font-size: 14px;
}

/* 套餐充值样式 */
.package-content {
  margin-top: 16px;
}

.channel-selector {
  margin-bottom: 20px;
}

.channel-selector .label {
  display: block;
  margin-bottom: 12px;
  font-weight: 600;
  color: #303133;
}

.package-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.package-item {
  border: 2px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
}

.package-item:hover {
  border-color: #409EFF;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.package-item.active {
  border-color: #409EFF;
  background: linear-gradient(135deg, #ecf5ff, #f0f9ff);
}

.package-item.active::after {
  content: '✓';
  position: absolute;
  top: 8px;
  right: 8px;
  width: 20px;
  height: 20px;
  background: #409EFF;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.package-amount {
  margin-bottom: 8px;
}

.package-amount .symbol {
  font-size: 14px;
  color: #409EFF;
  font-weight: 600;
}

.package-amount .value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.package-bonus {
  color: #67C23A;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}

.package-actual {
  color: #E6A23C;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.package-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.loading-packages {
  text-align: center;
  padding: 40px 0;
  color: #909399;
}

.loading-packages .el-icon {
  margin-right: 8px;
}

.no-packages,
.select-channel-tip {
  text-align: center;
  padding: 40px 0;
  color: #909399;
  font-size: 14px;
}
</style>
