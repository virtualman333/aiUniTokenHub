<template>
  <div class="quick-tags">
    <button 
      :class="{ active: featuredOnly }" 
      @click="$emit('toggle-featured')"
    >
      <i class="icon-star"></i> 推荐模型
    </button>
    <button 
      v-for="tag in tags" 
      :key="tag" 
      :class="{ active: selectedTags.includes(tag) }"
      @click="$emit('toggle-tag', tag)"
    >
      {{ tag }}
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  tags: string[]
  selectedTags: string[]
  featuredOnly: boolean
}>()

defineEmits<{
  'toggle-featured': []
  'toggle-tag': [tag: string]
}>()
</script>

<style scoped>
.quick-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.quick-tags button {
  padding: 8px 16px;
  border: 1px solid #e4e7ed;
  border-radius: 20px;
  background: white;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.quick-tags button:hover {
  border-color: #409eff;
  color: #409eff;
}

.quick-tags button.active {
  background: #409eff;
  border-color: #409eff;
  color: white;
}
</style>
