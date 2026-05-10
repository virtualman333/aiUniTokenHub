<template>
  <el-dialog v-model="visible" title="账户充值" width="700px" @close="handleClose">
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
      <el-button @click="visible = false">取消</el-button>
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
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import api from '@/stores'
import { fireConfetti } from '@/utils/confetti'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const visible = computed({
  get() {
    return props.modelValue
  },
  set(value: boolean) {
    emit('update:modelValue', value)
  }
})

const recharging = ref(false)
const payMethod = ref('card')
const cardCode = ref('')

// 充值渠道相关
const rechargeChannels = ref<any[]>([])
const selectedChannel = ref<number | null>(null)
const channelPackages = ref<any[]>([])
const loadingPackages = ref(false)
const selectedPackage = ref<number | null>(null)

// 加载充值渠道
async function loadRechargeChannels() {
  try {
    const res: any = await api.get('/users/recharge/channels/')
    rechargeChannels.value = res.data || res || []
    
    // 默认选择第一个渠道
    if (rechargeChannels.value.length > 0 && !selectedChannel.value) {
      selectedChannel.value = rechargeChannels.value[0].id
      loadChannelPackages(selectedChannel.value)
    }
  } catch (e) {
    console.error('加载充值渠道失败:', e)
    rechargeChannels.value = []
  }
}

// 加载渠道套餐
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

// 切换渠道
function handleChannelChange(channelId: number) {
  selectedPackage.value = null
  if (channelId) {
    loadChannelPackages(channelId)
  }
}

// 可用套餐
const selectedChannelPackages = computed(() => {
  return channelPackages.value.filter(pkg => pkg.is_active)
})

// 是否可以提交
const canSubmitPackage = computed(() => {
  return selectedPackage.value !== null && payMethod.value === 'package'
})

// 套餐充值
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
      window.open(res.redirect_url, '_blank')
      
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
        payMethod.value = 'card'
        visible.value = true
      }).catch(() => {
        // 用户点击"去支付"
      })
      
      visible.value = false
      return
    }
    
    ElMessage.success(res.message || '充值成功')
    visible.value = false
    selectedPackage.value = null
    emit('success')
    fireConfetti()
  } catch (e: any) {
    const errorMsg = e.response?.data?.msg || e.response?.data?.message || e.message || '充值失败'
    ElMessage.error(errorMsg)
  } finally {
    recharging.value = false
  }
}

// 卡密兑换
async function handleRedeemCard() {
  if (!cardCode.value.trim()) {
    ElMessage.warning('请输入卡密码')
    return
  }
  recharging.value = true
  try {
    const res: any = await api.post('/users/billing/redeem/', {
      code: cardCode.value.trim()
    })
    ElMessage.success(`卡密兑换成功，充值 ¥${res.card_amount}`)
    visible.value = false
    cardCode.value = ''
    emit('success')
    fireConfetti()
  } catch (e: any) {
    const errorMsg = e.response?.data?.msg || e.response?.data?.detail || e.message || '卡密兑换失败'
    ElMessage.error(errorMsg)
  } finally {
    recharging.value = false
  }
}

// 切换充值方式
function handlePayMethodChange() {
  cardCode.value = ''
  selectedPackage.value = null
}

// 关闭对话框
function handleClose() {
  cardCode.value = ''
  selectedPackage.value = null
  payMethod.value = 'card'
}

// 监听显示状态
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    loadRechargeChannels()
  }
})
</script>

<style scoped>
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
