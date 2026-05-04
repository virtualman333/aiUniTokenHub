<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">API列表</h2>
    </div>
    
    <!-- 分类筛选 -->
    <div class="filter-bar">
      <el-select v-model="selectedCategory" placeholder="选择分类" clearable @change="handleCategoryChange">
        <el-option label="全部" :value="null" />
        <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" />
      </el-select>
    </div>
    
    <!-- API列表 -->
    <div class="api-grid">
      <el-card v-for="api in endpoints" :key="api.id" class="api-card" shadow="hover">
        <template #header>
          <div class="api-header">
            <el-tag :type="getMethodType(api.method)" size="small">{{ api.method }}</el-tag>
            <span class="api-name">{{ api.name }}</span>
          </div>
        </template>
        <div class="api-path">{{ api.path }}</div>
        <div class="api-desc">{{ api.description || '暂无描述' }}</div>
        <template #footer>
          <div class="api-footer">
            <span class="api-rate">限 {{ api.rate_limit }}/min</span>
            <el-button type="primary" size="small" @click="viewDoc(api)">查看文档</el-button>
          </div>
        </template>
      </el-card>
    </div>
    
    <!-- 空状态 -->
    <el-empty v-if="!endpoints.length" description="暂无API" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAPIStore } from '@/stores'

const router = useRouter()
const apiStore = useAPIStore()

const categories = ref([])
const endpoints = ref([])
const selectedCategory = ref(null)

onMounted(async () => {
  categories.value = await apiStore.fetchCategories()
  endpoints.value = await apiStore.fetchEndpoints()
})

const handleCategoryChange = async () => {
  endpoints.value = await apiStore.fetchEndpoints(selectedCategory.value)
}

const getMethodType = (method) => {
  const types = {
    GET: '',
    POST: 'success',
    PUT: 'warning',
    DELETE: 'danger',
    PATCH: 'info'
  }
  return types[method] || ''
}

const viewDoc = (api) => {
  router.push(`/api-doc/${api.id}`)
}
</script>

<style lang="scss" scoped>
.filter-bar {
  margin-bottom: 20px;
}

.api-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.api-card {
  .api-header {
    display: flex;
    align-items: center;
    gap: 10px;
    
    .api-name {
      font-weight: 600;
    }
  }
  
  .api-path {
    font-family: monospace;
    font-size: 13px;
    color: #666;
    background: #f5f7fa;
    padding: 8px;
    border-radius: 4px;
    margin-bottom: 12px;
  }
  
  .api-desc {
    font-size: 14px;
    color: #999;
    line-height: 1.5;
  }
  
  .api-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .api-rate {
      font-size: 12px;
      color: #999;
    }
  }
}
</style>
