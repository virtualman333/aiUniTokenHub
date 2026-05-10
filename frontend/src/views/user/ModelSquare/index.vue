<template>
  <div class="model-square">
    <!-- 头部 -->
    <div class="header">
      <div class="header-content">
        <h1>模型广场</h1>
        <p class="subtitle">
          探索、对比、接入优质AI模型
          <el-button type="primary" @click="$router.push('/app/tutorial')" style="margin-left: 12px;">
            快速接入教程 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
        </p>
      </div>
    </div>

    <!-- 主体内容：左侧供应商 + 右侧模型列表 -->
    <div class="main-content">
      <!-- 左侧供应商侧边栏 -->
      <ProviderSidebar
        :providers="filters.providers"
        :selected-provider="selectedProvider"
        :total-models="total"
        @update:selected-provider="selectedProvider = $event"
      />

      <!-- 右侧内容 -->
      <div class="content-area">
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

        <!-- 模型列表 -->

        <!-- 模型列表 -->
        <div class="model-grid" v-loading="loading">
          <ModelCard
            v-for="model in models"
            :key="model.id"
            :model="model"
            @click="showModelDetail"
          />
        </div>

        <!-- 分页 -->
        <div v-if="total > 0" class="pagination">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[12, 20, 40, 60]"
            layout="total, sizes, prev, pager, next"
            @size-change="onPageChange"
            @current-change="onPageChange"
          />
        </div>

        <!-- 空状态 -->
        <div v-if="!loading && models.length === 0" class="empty-state">
          <el-empty description="暂无模型" />
        </div>
      </div>
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
import { ArrowRight } from '@element-plus/icons-vue'
import FilterBar from './components/FilterBar.vue'
import ProviderSidebar from './components/ProviderSidebar.vue'
import ModelCard from './components/ModelCard.vue'
import ModelDetail from './components/ModelDetail.vue'
import { useModels } from './composables/useModels'

const router = useRouter()
const {
  loading,
  models,
  filters,
  currentPage,
  pageSize,
  total,
  fetchFilters,
  fetchModels
} = useModels()

// 筛选状态
const searchQuery = ref('')
const selectedProvider = ref('')
const selectedCategory = ref('')
const selectedCapability = ref('')
const selectedTags = ref<string[]>([])
const commonTags = ref<string[]>([])

// 详情弹窗
const detailVisible = ref(false)
const currentModel = ref<Record<string, any> | null>(null)

onMounted(() => {
  fetchFilters()
  fetchModels()
})

// 监听筛选变化
import { watch } from 'vue'

watch([searchQuery, selectedProvider, selectedCategory], () => {
  debounceFetch()
})

function debounceFetch() {
  currentPage.value = 1
  const params: Record<string, string> = {}
  if (searchQuery.value) params.search = searchQuery.value
  if (selectedProvider.value) params.provider = selectedProvider.value
  if (selectedCategory.value) params.category = selectedCategory.value
  
  fetchModels(params)
}

function onPageChange() {
  const params: Record<string, string> = {}
  if (searchQuery.value) params.search = searchQuery.value
  if (selectedProvider.value) params.provider = selectedProvider.value
  if (selectedCategory.value) params.category = selectedCategory.value
  fetchModels(params)
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
  if (currentModel.value?.code) {
    router.push({ name: 'Chat', query: { model: currentModel.value.code } })
  } else {
    router.push({ name: 'Chat' })
  }
}
</script>

<style scoped>
.model-square {
  padding: var(--space-6);
  max-width: 1600px;
  margin: 0 auto;
  animation: fadeIn 0.5s ease-out;
}

.header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.header-content h1 {
  font-size: var(--text-4xl);
  font-weight: var(--font-bold);
  color: #000000;
  margin-bottom: var(--space-3);
  letter-spacing: -0.025em;
}

.subtitle {
  color: var(--text-secondary);
  font-size: var(--text-base);
  font-weight: var(--font-normal);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
}

/* 主体内容布局 */
.main-content {
  display: flex;
  gap: var(--space-6);
  align-items: flex-start;
}

.content-area {
  flex: 1;
  min-width: 0;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--space-6);
  min-height: 200px;
  margin-top: var(--space-6);
}

.pagination {
  margin-top: var(--space-8);
  display: flex;
  justify-content: center;
}

.empty-state {
  text-align: center;
  padding: var(--space-16) 0;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .main-content {
    flex-direction: column;
  }
  
  .model-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

@media (max-width: 768px) {
  .model-square {
    padding: var(--space-4);
  }
  
  .header-content h1 {
    font-size: var(--text-3xl);
  }
  
  .model-grid {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }
  
  .main-content {
    gap: var(--space-4);
  }
}
</style>
