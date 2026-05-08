<template>
  <div class="model-card" @click="$emit('click', model)">
    <!-- 标签 -->
    <div class="card-tags" v-if="model.is_new || model.is_featured">
      <span v-if="model.is_new" class="tag-new">NEW</span>
      <span v-if="model.is_featured" class="tag-featured">推荐</span>
    </div>
    
    <!-- 供应商logo -->
    <div class="card-header">
      <div class="provider-logo-wrapper">
        <img 
          v-if="model.provider_logo" 
          :src="model.provider_logo" 
          class="provider-logo"
          @error="handleImageError"
        />
        <div v-else class="provider-logo-placeholder">
          {{ model.provider_name?.charAt(0) }}
        </div>
      </div>
      <div class="provider-info">
        <span class="provider-name">{{ model.provider_name }}</span>
        <span class="model-name">{{ model.name }}</span>
      </div>
      <div class="model-version" v-if="model.version">
        v{{ model.version }}
      </div>
    </div>
    
    <!-- 描述 -->
    <p class="card-desc">{{ model.description || '暂无描述' }}</p>
    
    <!-- 功能标签 -->
    <div class="capabilities">
      <span v-if="model.supports_vision" class="cap-tag vision">
        <el-icon :size="12"><View /></el-icon>
        视觉
      </span>
      <span v-if="model.supports_streaming" class="cap-tag streaming">
        <el-icon :size="12"><VideoPlay /></el-icon>
        流式
      </span>
      <span v-if="model.supports_tools" class="cap-tag tools">
        <el-icon :size="12"><Tools /></el-icon>
        工具
      </span>
      <span v-if="model.supports_json" class="cap-tag json">
        <el-icon :size="12"><Document /></el-icon>
        JSON
      </span>
    </div>
    
    <!-- 价格 -->
    <div class="pricing">
      <div class="price-item">
        <span class="price-label">输入</span>
        <span class="price-value">
          ¥{{ formatPrice(model.input_price) }}/1M
        </span>
      </div>
      <div class="price-item" v-if="Number(model.cached_input_price) > 0">
        <span class="price-label">缓存</span>
        <span class="price-value cached">
          ¥{{ formatPrice(model.cached_input_price) }}/1M
        </span>
      </div>
      <div class="price-item">
        <span class="price-label">输出</span>
        <span class="price-value">
          ¥{{ formatPrice(model.output_price) }}/1M
        </span>
      </div>
    </div>
    
    <!-- 统计 -->
    <div class="card-footer">
      <div class="usage-count">
        <el-icon :size="14"><DataLine /></el-icon>
        <span>{{ formatNumber(model.usage_count) }} 次调用</span>
      </div>
      <div class="rating" v-if="model.rating">
        <el-icon :size="14"><Star /></el-icon>
        <span>{{ model.rating }}</span>
      </div>
      <div class="action-hint">
        <el-icon :size="14"><ArrowRight /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { 
  View, 
  VideoPlay, 
  Tools, 
  Document, 
  DataLine, 
  Star, 
  ArrowRight 
} from '@element-plus/icons-vue'

defineProps<{
  model: Record<string, any>
}>()

defineEmits<{
  click: [model: Record<string, any>]
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

function handleImageError(e: Event) {
  (e.target as HTMLElement).style.display = 'none'
}
</script>

<style scoped>
.model-card {
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  cursor: pointer;
  transition: all var(--transition-base);
  border: 1px solid var(--border-light);
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: var(--gradient-primary);
    opacity: 0;
    transition: opacity var(--transition-fast);
  }
  
  &:hover {
    transform: translateY(-6px);
    box-shadow: var(--shadow-lg);
    border-color: var(--primary-200);
    
    &::before {
      opacity: 1;
    }
    
    .action-hint {
      opacity: 1;
      transform: translateX(0);
    }
  }
}

.card-tags {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  display: flex;
  gap: var(--space-2);
  z-index: 1;
}

.tag-new {
  background: var(--error-500);
  color: var(--text-inverse);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  letter-spacing: 0.5px;
}

.tag-featured {
  background: var(--primary-500);
  color: var(--text-inverse);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.provider-logo-wrapper {
  position: relative;
}

.provider-logo {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-lg);
  object-fit: contain;
  background: var(--neutral-50);
  padding: var(--space-1);
}

.provider-logo-placeholder {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-lg);
  background: var(--gradient-primary);
  color: var(--text-inverse);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
}

.provider-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.provider-name {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  font-weight: var(--font-medium);
  margin-bottom: var(--space-1);
}

.model-name {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-version {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  background: var(--neutral-100);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  flex-shrink: 0;
}

.card-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
  margin-bottom: var(--space-4);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 44px;
}

.capabilities {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}

.cap-tag {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  
  &.vision {
    background: var(--primary-50);
    color: var(--primary-700);
    border: 1px solid var(--primary-100);
  }
  
  &.streaming {
    background: var(--success-50);
    color: var(--success-700);
    border: 1px solid var(--success-100);
  }
  
  &.tools {
    background: var(--warning-50);
    color: var(--warning-700);
    border: 1px solid var(--warning-100);
  }
  
  &.json {
    background: var(--accent-50);
    color: var(--accent-700);
    border: 1px solid var(--accent-100);
  }
}

.pricing {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4) 0;
  border-top: 1px solid var(--border-light);
  border-bottom: 1px solid var(--border-light);
  margin-bottom: var(--space-4);
}

.price-item {
  flex: 1;
  text-align: center;
}

.price-label {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  display: block;
  margin-bottom: var(--space-1);
  font-weight: var(--font-medium);
}

.price-value {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--primary-700);
  
  &.cached {
    color: var(--primary-700);
  }
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.usage-count,
.rating {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-weight: var(--font-medium);
}

.rating {
  color: var(--primary-700);
}

.action-hint {
  opacity: 0;
  transform: translateX(-8px);
  transition: all var(--transition-fast);
  color: var(--primary-500);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .model-card {
    padding: var(--space-4);
  }
  
  .card-header {
    flex-wrap: wrap;
  }
  
  .model-version {
    order: 3;
    margin-top: var(--space-2);
  }
  
  .pricing {
    flex-direction: column;
    gap: var(--space-2);
  }
  
  .price-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-2) 0;
    border-bottom: 1px dashed var(--border-light);
    
    &:last-child {
      border-bottom: none;
    }
  }
  
  .price-label {
    margin-bottom: 0;
  }
}
</style>
