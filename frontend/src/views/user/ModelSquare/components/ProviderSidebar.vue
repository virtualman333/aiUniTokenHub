<template>
  <div class="provider-sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-header" @click="toggleCollapse">
      <span class="title">供应商</span>
      <el-icon :class="{ 'is-rotate': isCollapsed }">
        <ArrowRight />
      </el-icon>
    </div>
    
    <div class="provider-list" v-show="!isCollapsed">
      <div 
        class="provider-item"
        :class="{ active: selectedProvider === '' }"
        @click="selectProvider('')"
      >
        <i class="icon-all"></i>
        <span>全部供应商</span>
        <span class="model-count">{{ totalModels }}</span>
      </div>
      
      <div 
        v-for="provider in providers"
        :key="provider.code"
        class="provider-item"
        :class="{ active: selectedProvider === provider.code }"
        @click="selectProvider(provider.code)"
      >
        <img 
          v-if="provider.logo" 
          :src="provider.logo" 
          class="provider-logo"
          :alt="provider.name"
        />
        <i v-else class="icon-provider"></i>
        <span>{{ provider.name }}</span>
        <span class="model-count">{{ provider.model_count || 0 }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'

defineProps<{
  providers: Array<{ code: string; name: string; logo?: string; model_count?: number }>
  selectedProvider: string
  totalModels: number
}>()

const emit = defineEmits<{
  'update:selectedProvider': [value: string]
}>()

const isCollapsed = ref(false)

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

function selectProvider(providerCode: string) {
  emit('update:selectedProvider', providerCode)
}
</script>

<style scoped>
.provider-sidebar {
  width: 240px;
  background: white;
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  overflow: hidden;
  transition: width 0.3s ease;
  flex-shrink: 0;
}

.provider-sidebar.collapsed {
  width: 48px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  cursor: pointer;
  border-bottom: 1px solid #e4e7ed;
  user-select: none;
}

.sidebar-header .title {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.sidebar-header .el-icon {
  transition: transform 0.3s ease;
  color: #909399;
}

.sidebar-header .el-icon.is-rotate {
  transform: rotate(90deg);
}

.provider-sidebar.collapsed .sidebar-header .title,
.provider-sidebar.collapsed .provider-item span,
.provider-sidebar.collapsed .provider-item .model-count {
  display: none;
}

.provider-list {
  padding: 8px 0;
  overflow-y: auto;
  max-height: calc(100vh - 300px);
}

.provider-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.provider-item:hover {
  background: #f5f7fa;
}

.provider-item.active {
  background: #ecf5ff;
  border-left-color: #409eff;
  color: #409eff;
}

.provider-logo {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  object-fit: contain;
}

.provider-item i {
  font-size: 18px;
  color: #909399;
}

.provider-item span {
  font-size: 14px;
  color: #606266;
  flex: 1;
}

.provider-item.active span {
  color: #409eff;
  font-weight: 500;
}

.model-count {
  font-size: 12px;
  color: #909399;
  background: #f0f2f5;
  padding: 2px 8px;
  border-radius: 10px;
  flex: none !important;
}

.provider-item.active .model-count {
  background: #409eff;
  color: white;
}

.provider-sidebar.collapsed .provider-item {
  justify-content: center;
  padding: 12px 0;
}

.provider-sidebar.collapsed .provider-logo,
.provider-sidebar.collapsed .provider-item i {
  margin: 0;
}
</style>
