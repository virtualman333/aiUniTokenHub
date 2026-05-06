<template>
  <el-dialog 
    :model-value="visible" 
    :title="model?.name" 
    width="700px"
    class="model-detail-dialog"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div v-if="model" class="model-detail">
      <div class="detail-header">
        <div class="detail-provider">
          <img 
            v-if="model.provider_logo" 
            :src="model.provider_logo" 
            class="provider-logo large"
          />
          <div v-else class="provider-logo-placeholder large">
            {{ model.provider_name?.charAt(0) }}
          </div>
          <div>
            <h3>{{ model.provider_name }}</h3>
            <p>{{ model.category_name || '未分类' }}</p>
          </div>
        </div>
        <div class="detail-status">
          <el-tag :type="getStatusType(model.status)">
            {{ getStatusText(model.status) }}
          </el-tag>
        </div>
      </div>
      
      <div class="detail-section">
        <h4>模型描述</h4>
        <p>{{ model.description || '暂无描述' }}</p>
      </div>
      
      <div class="detail-section">
        <h4>功能特性</h4>
        <div class="feature-list">
          <div class="feature-item">
            <span class="feature-name">上下文窗口</span>
            <span class="feature-value">{{ formatNumber(model.context_window) }} tokens</span>
          </div>
          <div class="feature-item">
            <span class="feature-name">最大输出</span>
            <span class="feature-value">{{ formatNumber(model.max_tokens) }} tokens</span>
          </div>
          <div class="feature-item">
            <span class="feature-name">流式输出</span>
            <span class="feature-value">{{ model.supports_streaming ? '支持' : '不支持' }}</span>
          </div>
          <div class="feature-item">
            <span class="feature-name">视觉理解</span>
            <span class="feature-value">{{ model.supports_vision ? '支持' : '不支持' }}</span>
          </div>
          <div class="feature-item">
            <span class="feature-name">工具调用</span>
            <span class="feature-value">{{ model.supports_tools ? '支持' : '不支持' }}</span>
          </div>
          <div class="feature-item">
            <span class="feature-name">JSON模式</span>
            <span class="feature-value">{{ model.supports_json ? '支持' : '不支持' }}</span>
          </div>
        </div>
      </div>
      
      <div class="detail-section">
        <h4>定价（元 / 百万 tokens）</h4>
        <div class="pricing-table">
          <div class="price-row">
            <span>输入</span>
            <strong>¥{{ formatPrice(model.input_price) }}</strong>
          </div>
          <div class="price-row" v-if="Number(model.cached_input_price) > 0">
            <span>缓存命中</span>
            <strong class="cached">¥{{ formatPrice(model.cached_input_price) }}</strong>
          </div>
          <div class="price-row">
            <span>输出</span>
            <strong>¥{{ formatPrice(model.output_price) }}</strong>
          </div>
        </div>
      </div>
      
      <div class="detail-section" v-if="model.tags?.length">
        <h4>标签</h4>
        <div class="tag-list">
          <el-tag v-for="tag in model.tags" :key="tag" size="small">
            {{ tag }}
          </el-tag>
        </div>
      </div>
    </div>
    
    <template #footer>
      <el-button @click="$emit('update:visible', false)">关闭</el-button>
      <el-button type="primary" @click="$emit('use')">
        <el-icon><ChatRound /></el-icon>
        开始对话
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ChatRound } from '@element-plus/icons-vue'

defineProps<{
  visible: boolean
  model: Record<string, any> | null
}>()

defineEmits<{
  'update:visible': [value: boolean]
  'use': []
}>()

function formatPrice(price: number | string | null): string {
  if (price === null || price === undefined || price === '' || Number(price) === 0) return '0'
  return parseFloat(String(price)).toFixed(2)
}

function formatNumber(num: number | string | null): string {
  if (!num) return '0'
  const n = Number(num)
  if (n >= 10000) {
    return (n / 10000).toFixed(1) + 'w'
  }
  return String(n)
}

function getStatusText(status: string): string {
  const map: Record<string, string> = {
    active: '已上架',
    inactive: '已下架',
    beta: '测试中'
  }
  return map[status] || status
}

function getStatusType(status: string): string {
  const map: Record<string, string> = {
    active: 'success',
    inactive: 'info',
    beta: 'warning'
  }
  return map[status] || 'info'
}
</script>

<style scoped>
.model-detail {
  padding: 0 8px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.detail-provider {
  display: flex;
  align-items: center;
  gap: 16px;
}

.provider-logo.large {
  width: 64px;
  height: 64px;
}

.provider-logo-placeholder.large {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
}

.detail-provider h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
}

.detail-provider p {
  margin: 0;
  color: #909399;
  font-size: 13px;
}

.detail-section {
  margin-bottom: 20px;
}

.detail-section h4 {
  font-size: 14px;
  color: #909399;
  margin-bottom: 12px;
  font-weight: normal;
}

.detail-section p {
  color: #606266;
  line-height: 1.6;
}

.feature-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.feature-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
}

.feature-name {
  color: #606266;
  font-size: 13px;
}

.feature-value {
  color: #1a1a2e;
  font-weight: 500;
  font-size: 13px;
}

.pricing-table {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
}

.price-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
}

.price-row:last-child {
  border-top: 1px solid #e4e7ed;
  margin-top: 8px;
  padding-top: 12px;
}

.price-row strong {
  color: #f56c6c;
  font-size: 16px;
}

.price-row strong.cached {
  color: #10b981;
}

.tag-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
