<template>
  <div class="model-card" @click="$emit('click', model)">
    <!-- 标签 -->
    <div class="card-tags" v-if="model.is_new || model.is_featured">
      <span v-if="model.is_new" class="tag-new">NEW</span>
      <span v-if="model.is_featured" class="tag-featured">推荐</span>
    </div>
    
    <!-- 供应商logo -->
    <div class="card-header">
      <img 
        v-if="model.provider_logo" 
        :src="model.provider_logo" 
        class="provider-logo"
        @error="handleImageError"
      />
      <div v-else class="provider-logo-placeholder">
        {{ model.provider_name?.charAt(0) }}
      </div>
      <div class="provider-info">
        <span class="provider-name">{{ model.provider_name }}</span>
        <span class="model-name">{{ model.name }}</span>
      </div>
    </div>
    
    <!-- 描述 -->
    <p class="card-desc">{{ model.description || '暂无描述' }}</p>
    
    <!-- 功能标签 -->
    <div class="capabilities">
      <span v-if="model.supports_vision" class="cap-tag">
        <i class="icon-eye"></i> 视觉
      </span>
      <span v-if="model.supports_streaming" class="cap-tag">
        <i class="icon-stream"></i> 流式
      </span>
      <span v-if="model.supports_tools" class="cap-tag">
        <i class="icon-tools"></i> 工具
      </span>
      <span v-if="model.supports_json" class="cap-tag">
        <i class="icon-json"></i> JSON
      </span>
    </div>
    
    <!-- 价格 -->
    <div class="pricing">
      <div class="price-item">
        <span class="price-label">输入</span>
        <span class="price-value">
          ¥{{ formatPrice(model.input_price) }}/1K tokens
        </span>
      </div>
      <div class="price-item">
        <span class="price-label">输出</span>
        <span class="price-value">
          ¥{{ formatPrice(model.output_price) }}/1K tokens
        </span>
      </div>
    </div>
    
    <!-- 统计 -->
    <div class="card-footer">
      <span class="usage-count">
        <i class="icon-chart"></i>
        {{ formatNumber(model.usage_count) }} 次调用
      </span>
      <span class="rating">
        <i class="icon-star"></i>
        {{ model.rating }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  model: Record<string, any>
}>()

defineEmits<{
  click: [model: Record<string, any>]
}>()

function formatPrice(price: number | string | null): string {
  if (!price || price == 0) return '0.00'
  return parseFloat(String(price)).toFixed(6)
}

function formatNumber(num: number | string | null): string {
  if (!num) return '0'
  const n = Number(num)
  if (n >= 10000) {
    return (n / 10000).toFixed(1) + 'w'
  }
  return String(n)
}

function handleImageError(e: Event) {
  (e.target as HTMLElement).style.display = 'none'
}
</script>

<style scoped>
.model-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid #f0f0f0;
  position: relative;
}

.model-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  border-color: #409eff;
}

.card-tags {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  gap: 6px;
}

.tag-new {
  background: #f56c6c;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.tag-featured {
  background: #409eff;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.provider-logo {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  object-fit: contain;
}

.provider-logo-placeholder {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
}

.provider-info {
  display: flex;
  flex-direction: column;
}

.provider-name {
  font-size: 12px;
  color: #909399;
}

.model-name {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.card-desc {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 42px;
}

.capabilities {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.cap-tag {
  padding: 4px 8px;
  background: #f0f9ff;
  color: #409eff;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.pricing {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-top: 1px solid #f0f0f0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 12px;
}

.price-item {
  flex: 1;
}

.price-label {
  font-size: 12px;
  color: #909399;
  display: block;
  margin-bottom: 2px;
}

.price-value {
  font-size: 14px;
  font-weight: 600;
  color: #f56c6c;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.rating {
  color: #f5a623;
}
</style>
