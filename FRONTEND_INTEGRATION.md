# 多充值入口功能 - 前端对接说明

## 功能概述

已实现"用户端卡密方式充值支持多个充值入口，后台可配置"的功能。

## 前端页面结构

### 1. 用户端 - 账单中心 (views/user/Billing/index.vue)
- 保留原有的卡密充值功能
- 新增"套餐充值"标签页
- 支持选择充值渠道和套餐

### 2. 管理端 - 充值管理 (views/admin/RechargeManagement.vue)
- 充值渠道管理（增删改查）
- 充值套餐管理（增删改查）
- 渠道筛选和统计

## 路由配置

### 用户端
- 账单中心: `/app/billing` (已存在)

### 管理端
- 充值管理: `/admin/recharge-management` (新增)

## API 调用

### 用户端 API

#### 1. 获取充值渠道列表
```javascript
import api from '@/stores'

const res = await api.get('/users/recharge/channels/')
// 返回数据示例
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "name": "官方充值",
      "code": "official",
      "description": "官方充值渠道，安全可靠",
      "icon": "",
      "is_active": true,
      "sort_order": 0,
      "package_count": 3,
      "created_at": "2026-05-10T10:00:00Z"
    }
  ],
  "message": "获取成功"
}
```

#### 2. 获取充值套餐列表
```javascript
const res = await api.get('/users/recharge/packages/', {
  params: { channel_id: 1 }  // 可选参数
})
// 返回数据示例
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "channel": 1,
      "channel_name": "官方充值",
      "amount": 100.00,
      "bonus": 10.00,
      "actual_amount": 110.00,
      "is_active": true,
      "sort_order": 0,
      "description": "充100送10",
      "created_at": "2026-05-10T10:00:00Z"
    }
  ],
  "message": "获取成功"
}
```

#### 3. 提交充值
```javascript
const res = await api.post('/users/recharge/submit/', {
  package_id: 1,        // 充值套餐ID（可选）
  channel_id: 1,       // 充值渠道ID（可选）
  amount: 200.00        // 自定义金额（可选，与package_id二选一）
})
// 返回数据示例
{
  "code": 0,
  "data": {
    "bill": {
      "id": 1,
      "type": "recharge",
      "type_display": "充值",
      "amount": 110.00,
      "balance": 111.00,
      "description": "充值（套餐） - 官方充值",
      "created_at": "2026-05-10T10:00:00Z"
    },
    "balance": 111.00
  },
  "message": "充值成功，当前余额 ¥111.00"
}
```

### 管理员 API

#### 1. 获取充值渠道列表
```javascript
const res = await api.get('/users/admin/recharge/list_channels/')
```

#### 2. 创建充值渠道
```javascript
const res = await api.post('/users/admin/recharge/create_channel/', {
  name: "官方充值",
  code: "official",
  description: "官方充值渠道",
  icon: "",
  is_active: true,
  sort_order: 0
})
```

#### 3. 更新充值渠道
```javascript
const res = await api.put('/users/admin/recharge/update_channel/1/', {
  name: "官方充值（新版）",
  description: "更新后的描述"
})
```

#### 4. 删除充值渠道
```javascript
const res = await api.delete('/users/admin/recharge/delete_channel/1/')
```

#### 5. 获取充值套餐列表
```javascript
const res = await api.get('/users/admin/recharge/list_packages/', {
  params: { channel_id: 1 }  // 可选
})
```

#### 6. 创建充值套餐
```javascript
const res = await api.post('/users/admin/recharge/create_package/', {
  channel_id: 1,
  amount: 100.00,
  bonus: 10.00,
  description: "充100送10",
  is_active: true,
  sort_order: 0
})
```

#### 7. 更新充值套餐
```javascript
const res = await api.put('/users/admin/recharge/update_package/1/', {
  amount: 200.00,
  bonus: 20.00
})
```

#### 8. 删除充值套餐
```javascript
const res = await api.delete('/users/admin/recharge/delete_package/1/')
```

## 前端组件使用示例

### 用户端充值组件示例

```vue
<template>
  <el-dialog v-model="showRecharge" title="账户充值" width="700px">
    <el-tabs v-model="payMethod">
      <el-tab-pane label="卡密充值" name="card">
        <!-- 卡密充值表单 -->
      </el-tab-pane>
      <el-tab-pane label="套餐充值" name="package">
        <!-- 充值渠道选择 -->
        <el-radio-group v-model="selectedChannel" @change="handleChannelChange">
          <el-radio-button
            v-for="ch in rechargeChannels"
            :key="ch.id"
            :value="ch.id"
          >
            {{ ch.name }}
          </el-radio-button>
        </el-radio-group>

        <!-- 套餐列表 -->
        <div class="package-grid">
          <div
            v-for="pkg in selectedChannelPackages"
            :key="pkg.id"
            class="package-item"
            :class="{ active: selectedPackage === pkg.id }"
            @click="selectedPackage = pkg.id"
          >
            <div class="package-amount">
              ¥{{ Number(pkg.amount).toFixed(0) }}
            </div>
            <div v-if="pkg.bonus > 0" class="package-bonus">
              送 ¥{{ Number(pkg.bonus).toFixed(0) }}
            </div>
            <div class="package-actual">
              到账 ¥{{ Number(pkg.actual_amount).toFixed(2) }}
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/stores'

const showRecharge = ref(false)
const payMethod = ref('card')
const rechargeChannels = ref([])
const selectedChannel = ref(null)
const channelPackages = ref([])
const selectedPackage = ref(null)

onMounted(() => {
  loadRechargeChannels()
})

async function loadRechargeChannels() {
  const res = await api.get('/users/recharge/channels/')
  rechargeChannels.value = res.data || res || []
}

async function loadChannelPackages(channelId) {
  const res = await api.get('/users/recharge/packages/', {
    params: { channel_id: channelId }
  })
  channelPackages.value = res.data || res || []
}

function handleChannelChange(channelId) {
  selectedPackage.value = null
  if (channelId) {
    loadChannelPackages(channelId)
  }
}

const selectedChannelPackages = computed(() => {
  return channelPackages.value.filter(pkg => pkg.is_active)
})

async function handlePackageRecharge() {
  if (!selectedPackage.value) {
    return
  }

  await api.post('/users/recharge/submit/', {
    package_id: selectedPackage.value,
    channel_id: selectedChannel.value
  })
}
</script>
```

### 管理端充值管理页面示例

```vue
<template>
  <div class="recharge-management">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="充值渠道" name="channels">
        <!-- 渠道管理表格 -->
      </el-tab-pane>
      <el-tab-pane label="充值套餐" name="packages">
        <!-- 套餐管理表格 -->
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '@/stores'

const activeTab = ref('channels')
const channels = ref([])
const packages = ref([])

async function loadChannels() {
  const res = await api.get('/users/admin/recharge/list_channels/')
  channels.value = res.data || res || []
}

async function loadPackages() {
  const res = await api.get('/users/admin/recharge/list_packages/')
  packages.value = res.data || res || []
}

// 创建渠道
async function createChannel(data) {
  await api.post('/users/admin/recharge/create_channel/', data)
}

// 更新渠道
async function updateChannel(id, data) {
  await api.put(`/users/admin/recharge/update_channel/${id}/`, data)
}

// 删除渠道
async function deleteChannel(id) {
  await api.delete(`/users/admin/recharge/delete_channel/${id}/`)
}

// 创建套餐
async function createPackage(data) {
  await api.post('/users/admin/recharge/create_package/', data)
}

// 更新套餐
async function updatePackage(id, data) {
  await api.put(`/users/admin/recharge/update_package/${id}/`, data)
}

// 删除套餐
async function deletePackage(id) {
  await api.delete(`/users/admin/recharge/delete_package/${id}/`)
}
</script>
```

## 状态管理

如需在全局状态中管理充值渠道和套餐，可以在 store 中添加：

```javascript
// stores/index.js 或新建 stores/recharge.js
import { defineStore } from 'pinia'
import api from './api'

export const useRechargeStore = defineStore('recharge', {
  state: () => ({
    channels: [],
    packages: [],
    loading: false
  }),

  actions: {
    async loadChannels() {
      this.loading = true
      try {
        const res = await api.get('/users/recharge/channels/')
        this.channels = res.data || res || []
      } finally {
        this.loading = false
      }
    },

    async loadPackages(channelId) {
      this.loading = true
      try {
        const res = await api.get('/users/recharge/packages/', {
          params: channelId ? { channel_id: channelId } : {}
        })
        this.packages = res.data || res || []
      } finally {
        this.loading = false
      }
    },

    async submitRecharge(packageId, channelId) {
      const res = await api.post('/users/recharge/submit/', {
        package_id: packageId,
        channel_id: channelId
      })
      return res
    }
  }
})
```

## 路由守卫

已添加充值管理页面到路由配置：

```javascript
// router/index.js
{
  path: '/admin/recharge-management',
  name: 'RechargeManagement',
  component: () => import('@/views/admin/RechargeManagement.vue'),
  meta: { title: '充值管理', noIndex: true }
}
```

## 权限控制

- 用户端接口需要登录认证
- 管理端接口需要管理员权限

## 错误处理

所有 API 调用都应该包含错误处理：

```javascript
try {
  const res = await api.get('/users/recharge/channels/')
  // 处理成功
} catch (e) {
  if (e.response) {
    // 服务器返回错误
    console.error('错误信息:', e.response.data.message || e.response.data.msg)
  } else {
    // 网络错误
    console.error('网络错误:', e.message)
  }
}
```

## 最佳实践

1. **缓存策略**: 充值渠道列表变化不频繁，可以在本地缓存一段时间
2. **加载状态**: 发起请求时显示 loading 状态
3. **错误提示**: 使用 ElMessage 显示错误信息
4. **表单验证**: 提交前验证必填字段
5. **确认操作**: 删除等危险操作前显示确认对话框
6. **成功反馈**: 操作成功后显示成功提示，并刷新数据
7. **用户体验**: 充值成功后可以显示彩屑效果（如 fireConfetti）

## 数据库迁移

首次使用需要执行数据库迁移：

```bash
cd backend
python manage.py migrate users
```

## 注意事项

1. 删除充值渠道前，必须先删除该渠道下的所有套餐
2. 套餐的 channel_id 不能为空
3. 渠道代码（code）必须唯一
4. 金额必须大于 0
5. 邀请返利机制在充值时仍然生效
6. 账单记录会关联充值渠道，便于统计

## 测试建议

1. 创建充值渠道
2. 创建充值套餐
3. 用户端选择渠道和套餐进行充值
4. 验证账单记录是否正确关联渠道
5. 测试管理员的增删改查功能
6. 测试权限控制（非管理员不能访问管理接口）
