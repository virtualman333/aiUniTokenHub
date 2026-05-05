<template>
  <div class="model-square">
    <!-- 头部 -->
    <div class="header">
      <h1>模型广场</h1>
      <p class="subtitle">探索、对比、接入优质AI模型</p>
    </div>

    <!-- 筛选栏 -->
    <FilterBar
      v-model:search-query="searchQuery"
      v-model:selected-provider="selectedProvider"
      v-model:selected-category="selectedCategory"
      v-model:selected-capability="selectedCapability"
      :providers="filters.providers"
      :categories="filters.categories"
      :capabilities="filters.capabilities"
    />

    <!-- 快速标签 -->
    <QuickTags
      :tags="commonTags"
      :selected-tags="selectedTags"
      :featured-only="featuredOnly"
      @toggle-featured="toggleFeatured"
      @toggle-tag="toggleTag"
    />

    <!-- 模型列表 -->
    <div class="model-grid" v-loading="loading">
      <ModelCard
        v-for="model in models"
        :key="model.id"
        :model="model"
        @click="showModelDetail"
      />
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && models.length === 0" class="empty-state">
      <el-empty description="暂无模型" />
    </div>

    <!-- 模型详情弹窗 -->
    <ModelDetail
      v-model:visible="detailVisible"
      :model="currentModel"
      @use="useModel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import FilterBar from './components/FilterBar.vue'
import QuickTags from './components/QuickTags.vue'
import ModelCard from './components/ModelCard.vue'
import ModelDetail from './components/ModelDetail.vue'
import { useModels } from './composables/useModels'

const router = useRouter()
const {
  loading,
  models,
  filters,
  fetchFilters,
  fetchModels
} = useModels()

// 筛选状态
const searchQuery = ref('')
const selectedProvider = ref('')
const selectedCategory = ref('')
const selectedCapability = ref('')
const featuredOnly = ref(false)
const selectedTags = ref<string[]>([])
const commonTags = ['免费', 'GPT-4', 'Claude', '国产', '开源']

// 详情弹窗
const detailVisible = ref(false)
const currentModel = ref<Record<string, any> | null>(null)

onMounted(() => {
  fetchFilters()
  fetchModels()
})

// 监听筛选变化
import { watch } from 'vue'

watch([searchQuery, selectedProvider, selectedCategory, featuredOnly], () => {
  debounceFetch()
})

function debounceFetch() {
  const params: Record<string, string> = {}
  if (searchQuery.value) params.search = searchQuery.value
  if (selectedProvider.value) params.provider = selectedProvider.value
  if (selectedCategory.value) params.category = selectedCategory.value
  if (featuredOnly.value) params.featured = 'true'
  
  fetchModels(params)
}

function toggleFeatured() {
  featuredOnly.value = !featuredOnly.value
  debounceFetch()
}

function toggleTag(tag: string) {
  const idx = selectedTags.value.indexOf(tag)
  if (idx > -1) {
    selectedTags.value.splice(idx, 1)
  } else {
    selectedTags.value.push(tag)
  }
  debounceFetch()
}

function showModelDetail(model: Record<string, any>) {
  currentModel.value = model
  detailVisible.value = true
}

function useModel() {
  detailVisible.value = false
  router.push({ name: 'APIDoc' })
}
</script>

<style scoped>
.model-square {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.header h1 {
  font-size: 32px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
  font-size: 16px;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  min-height: 200px;
}

.empty-state {
  text-align: center;
  padding: 60px 0;
}
</style>
