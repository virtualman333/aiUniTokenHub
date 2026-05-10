<template>
  <div class="tags-view">
    <!-- 左滚动 -->
    <div class="scroll-btn left" v-show="showLeftBtn" @click="scrollBy(-200)">
      <el-icon><CaretLeft /></el-icon>
    </div>

    <!-- 标签列表 -->
    <div class="tags-list" ref="listRef" @wheel.prevent.stop="onWheel">
      <router-link
        v-for="tag in visitedTags"
        :key="tag.path"
        :to="tag.path"
        class="tag-item"
        :class="{ active: isActive(tag), affix: tag.affix }"
        @contextmenu.prevent="onContextMenu($event, tag)"
      >
        <span class="tag-title">{{ tag.title }}</span>
        <span
          v-if="!tag.affix"
          class="close-icon"
          @click.prevent.stop="removeTag(tag)"
        >
          <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M3 3l6 6M9 3l-6 6"/></svg>
        </span>
      </router-link>
    </div>

    <!-- 右滚动 -->
    <div class="scroll-btn right" v-show="showRightBtn" @click="scrollBy(200)">
      <el-icon><CaretRight /></el-icon>
    </div>

    <!-- 右键菜单 -->
    <Teleport to="body">
      <div v-if="menuVisible" class="ctx-menu" :style="{ top: menuY + 'px', left: menuX + 'px' }">
        <button @click="doRefresh">🔄 刷新</button>
        <button v-if="ctxTag?.affix !== true" @click="doCloseCurrent" class="danger">✕ 关闭当前</button>
        <hr />
        <button @click="doCloseOthers">关闭其他</button>
        <button @click="doCloseLeft">关闭左侧</button>
        <button @click="doCloseRight">关闭右侧</button>
        <hr />
        <button @click="doCloseAll">全部关闭</button>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CaretLeft, CaretRight } from '@element-plus/icons-vue'
import { getAffixTags, findMenuItem } from '@/config/adminMenu'

const route = useRoute()
const router = useRouter()
defineEmits(['refresh'])

// ─── 标签列表 ───
const visitedTags = ref(getAffixTags())
const listRef = ref(null)
const showLeftBtn = ref(false)
const showRightBtn = ref(false)

function isActive(t) { return t.path === route.path }

function addTag() {
  if (!route.path.startsWith('/admin')) return
  if (visitedTags.value.some(t => t.path === route.path)) return
  const m = findMenuItem(route.path)
  visitedTags.value.push({
    path: route.path,
    title: route.meta?.title || m?.title || '未命名',
    name: route.name,
    affix: !!m?.affix,
  })
  nextTick(scrollToActive)
}

function removeTag(tag) {
  const idx = visitedTags.value.findIndex(t => t.path === tag.path)
  if (idx < 0) return
  visitedTags.value.splice(idx, 1)
  if (isActive(tag)) {
    const nxt = visitedTags.value[idx] || visitedTags.value[idx - 1]
    if (nxt) router.push(nxt.path)
  }
}

// ─── 滚动 ───
function scrollBy(dx) { listRef.value?.scrollBy({ left: dx, behavior: 'smooth' }) }
function onWheel(e) { listRef.value?.scrollBy({ left: e.deltaY, behavior: 'auto' }) }

function updateScrollState() {
  const el = listRef.value
  if (!el) return
  showLeftBtn.value = el.scrollLeft > 2
  showRightBtn.value = el.scrollWidth - el.scrollLeft - el.clientWidth > 2
}

function scrollToActive() {
  const el = listRef.value
  if (!el) return
  const activeEl = el.querySelector('.tag-item.active')
  if (!activeEl) return
  const wr = el.getBoundingClientRect(), tr = activeEl.getBoundingClientRect()
  if (tr.left < wr.left + 4) el.scrollBy({ left: tr.left - wr.left - 8, behavior: 'smooth' })
  else if (tr.right > wr.right - 4) el.scrollBy({ left: tr.right - wr.right + 8, behavior: 'smooth' })
}

// ─── 右键菜单 ───
const menuVisible = ref(false)
const menuX = ref(0)
const menuY = ref(0)
let ctxTag = null

function onContextMenu(e, tag) {
  ctxTag = tag
  // 防止超出视口
  menuX.value = Math.min(e.clientX, window.innerWidth - 160)
  menuY.value = Math.min(e.clientY, window.innerHeight - 280)
  menuVisible.value = true
}
function hideMenu() { menuVisible.value = false; ctxTag = null }

/** 暴露给父组件：已访问的路由名列表（用于 keep-alive include） */
defineExpose({ getVisitedNames: () => visitedTags.value.map(t => t.name).filter(Boolean) })
function doRefresh() { hideMenu(); emit('refresh') }
function doCloseCurrent() { hideMenu(); ctxTag && !ctxTag.affix && removeTag(ctxTag) }
function doCloseOthers() {
  hideMenu()
  if (!ctxTag) return
  visitedTags.value = visitedTags.value.filter(t => t.affix || t.path === ctxTag.path)
  if (!isActive(ctxTag)) router.push(ctxTag.path)
}
function doCloseLeft() {
  hideMenu()
  if (!ctxTag) return
  const i = visitedTags.value.findIndex(t => t.path === ctxTag.path)
  visitedTags.value = visitedTags.value.filter((t, idx) => t.affix || idx >= i)
}
function doCloseRight() {
  hideMenu()
  if (!ctxTag) return
  const i = visitedTags.value.findIndex(t => t.path === ctxTag.path)
  visitedTags.value = visitedTags.value.filter((t, idx) => t.affix || idx <= i)
}
function doCloseAll() {
  hideMenu()
  visitedTags.value = visitedTags.value.filter(t => t.affix)
  const last = visitedTags.value[visitedTags.value.length - 1]
  router.push(last ? last.path : '/admin')
}

// ─── 生命周期 ───
watch(() => route.path, addTag)
watch(menuVisible, val => {
  if (val) document.addEventListener('click', hideMenu)
  else document.removeEventListener('click', hideMenu)
})

onMounted(() => {
  addTag()
  const el = listRef.value
  if (el) {
    el.addEventListener('scroll', updateScrollState)
    window.addEventListener('resize', updateScrollState)
  }
})
onBeforeUnmount(() => {
  const el = listRef.value
  if (el) {
    el.removeEventListener('scroll', updateScrollState)
    window.removeEventListener('resize', updateScrollState)
  }
})
</script>

<style scoped>
.tags-view {
  display: flex;
  align-items: center;
  height: 38px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
  user-select: none;
  position: relative;
  z-index: 10;
}

/* ── 滚动按钮 ── */
.scroll-btn {
  width: 22px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; border-radius: 4px; flex-shrink: 0;
  color: #a0a0a0; font-size: 14px; margin: 0 2px;
  transition: all .15s;
  &:hover { color: #409eff; background: #f0f5ff; }
}

/* ── 标签列表 ── */
.tags-list {
  flex: 1;
  display: flex;
  align-items: flex-end;
  gap: 5px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0 10px;
  scrollbar-width: none;
  &::-webkit-scrollbar { display: none; height: 0; }
}

/* ── 单个标签 ── */
.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 32px;
  padding: 0 14px;
  font-size: 13px;
  line-height: 1;
  color: #666;
  text-decoration: none;
  border-radius: 8px 8px 0 0;
  border: 1px solid transparent;
  border-bottom-color: #e8e8e8;
  background: transparent;
  white-space: nowrap;
  cursor: pointer;
  transition: all .18s ease;
  flex-shrink: 0;

  &:hover {
    color: #333;
    background: #f7f8fa;
    .close-icon { opacity: .65; }
  }

  &.active {
    color: #16a34a;
    background: #f0fdf4;
    border-color: #c6f6d5;
    border-bottom-color: transparent;
    box-shadow: inset 0 -2px 0 0 #16a34a;
    z-index: 1;
    .close-icon { opacity: .45; }
  }
  &.affix .close-icon { display: none; }
}

.tag-title {
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: .3px;
}

.close-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 15px; height: 15px;
  border-radius: 50%;
  opacity: 0;
  transition: all .15s;
  svg { width: 9px; height: 9px; }
  &:hover {
    background: #e54d42;
    color: #fff;
    opacity: 1 !important;
  }
}

/* ── 右键菜单（Teleport 到 body） ── */
.ctx-menu {
  position: fixed;
  z-index: 10000;
  min-width: 150px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 6px 24px rgba(0,0,0,.12), 0 0 1px rgba(0,0,0,.08);
  padding: 6px 0;
  animation: ctxIn .12s cubic-bezier(.2,.8,.2,1);
}
@keyframes ctxIn {
  from { opacity: 0; transform: scale(.94); }
  to   { opacity: 1; transform: scale(1); }
}

.ctx-menu button {
  display: flex; align-items: center; gap: 8px;
  width: 100%; padding: 8px 14px;
  font-size: 13px; color: #374151;
  border: none; background: none;
  cursor: pointer;
  transition: background .12s;
  &:hover { background: #f3f4f6; }
  &.danger:hover { background: #fef2f2; color: #dc2626; }
}
.ctx-menu hr {
  border: none; border-top: 1px solid #f0eff4;
  margin: 3px 8px;
}
</style>
