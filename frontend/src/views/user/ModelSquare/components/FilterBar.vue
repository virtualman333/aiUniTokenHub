<template>
  <div class="filter-bar">
    <!-- 搜索框 -->
    <div class="search-box">
      <i class="icon-search"></i>
      <input 
        :value="searchQuery"
        type="text" 
        placeholder="搜索模型名称、描述..."
        @input="$emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
      />
    </div>
    
    <!-- 筛选下拉 -->
    <div class="filter-group">
      <select 
        :value="selectedProvider"
        @change="$emit('update:selectedProvider', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">全部供应商</option>
        <option v-for="p in providers" :key="p.code" :value="p.code">
          {{ p.name }}
        </option>
      </select>
      
      <select 
        :value="selectedCategory"
        @change="$emit('update:selectedCategory', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">全部分类</option>
        <option v-for="c in categories" :key="c.code" :value="c.code">
          {{ c.name }}
        </option>
      </select>
      
      <select 
        :value="selectedCapability"
        @change="$emit('update:selectedCapability', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">全部功能</option>
        <option v-for="cap in capabilities" :key="cap.code" :value="cap.code">
          {{ cap.name }}
        </option>
      </select>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  searchQuery: string
  selectedProvider: string
  selectedCategory: string
  selectedCapability: string
  providers: Array<{ code: string; name: string }>
  categories: Array<{ code: string; name: string }>
  capabilities: Array<{ code: string; name: string }>
}>()

defineEmits<{
  'update:searchQuery': [value: string]
  'update:selectedProvider': [value: string]
  'update:selectedCategory': [value: string]
  'update:selectedCapability': [value: string]
}>()
</script>

<style scoped>
.filter-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.search-box {
  flex: 1;
  min-width: 300px;
  position: relative;
}

.search-box input {
  width: 100%;
  padding: 12px 16px 12px 44px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.search-box input:focus {
  outline: none;
  border-color: #409eff;
}

.search-box i {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: #909399;
}

.filter-group {
  display: flex;
  gap: 12px;
}

.filter-group select {
  padding: 10px 32px 10px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  min-width: 140px;
}

@media (max-width: 768px) {
  .filter-bar {
    gap: 12px;
  }

  .search-box {
    flex-basis: 100%;
    min-width: 0;
  }

  .filter-group {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .filter-group select {
    width: 100%;
    min-width: 0;
    padding-right: 24px;
  }
}

@media (max-width: 480px) {
  .filter-group {
    grid-template-columns: 1fr;
  }
}
</style>
