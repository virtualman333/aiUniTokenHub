<template>
  <div class="admin-layout">
    <!-- 顶部一级分类导航 -->
    <header class="top-nav">
      <div class="nav-left">
        <!-- Logo + 独立页面入口 -->
        <div class="brand" @click="router.push('/admin')">
          <img :src="logoSrc" alt="logo" class="logo-img" />
          <span class="brand-text">uniTokenHub</span>
        </div>
        <!-- 一级分类 -->
        <nav class="group-nav">
          <template v-for="g in menuGroups" :key="g.key">
            <a
              class="group-item"
              :class="{ active: activeGroupKey === g.key }"
              href="javascript:void(0)"
              @click="switchGroup(g)"
            >
              <el-icon><component :is="g.icon" /></el-icon>
              <span>{{ g.title }}</span>
            </a>
          </template>
        </nav>
      </div>
      <div class="nav-right">
        <ThemeToggle />
        <LangToggle />
        <el-button text size="small" @click="goToUser">
          <el-icon><Back /></el-icon> 返回用户端
        </el-button>
        <el-dropdown @command="handleCommand">
          <div class="user-info">
            <div class="avatar">{{ userStore.user?.username?.[0]?.toUpperCase() || 'A' }}</div>
            <span class="username">{{ userStore.user?.username }}</span>
            <el-icon><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人设置</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 主内容区（左侧子菜单 + 右侧内容） -->
    <div class="main-wrapper">
      <!-- 左侧子菜单 -->
      <aside class="submenu-sidebar" v-if="currentGroupChildren.length > 0">
        <nav class="submenu-list">
          <router-link
            v-for="item in currentGroupChildren"
            :key="item.path"
            :to="item.path"
            class="submenu-item"
            :class="{ active: route.path === item.path }"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </router-link>
        </nav>
      </aside>

      <!-- 右侧内容 -->
      <div class="content-area">
        <!-- 顶部信息栏 -->
        <div class="topbar">
          <h1 class="page-title">{{ currentTitle }}</h1>
          <div class="topbar-actions">
            <el-button
              v-if="route.path !== '/admin'"
              size="small"
              circle
              title="刷新"
              @click="handleRefresh"
            >
              <el-icon><RefreshRight /></el-icon>
            </el-button>
          </div>
        </div>

        <!-- 多标签页 -->
        <TagsView ref="tagsViewRef" @refresh="handleRefresh" />

        <!-- 内容区 -->
        <main class="content">
          <router-view v-slot="{ Component, route: curRoute }">
            <keep-alive :include="cachedViews">
              <component :is="Component" v-if="curRoute.path && !routeRefreshing" :key="curRoute.name || curRoute.path" />
            </keep-alive>
          </router-view>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores'
import {
  ArrowDown, Back, RefreshRight
} from '@element-plus/icons-vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import LangToggle from '@/components/LangToggle.vue'
import TagsView from '@/components/admin/TagsView.vue'
import { menuGroups, standalonePages, findGroupByPath, findMenuItem } from '@/config/adminMenu'
import logoSrc from '@/assets/image/logo.png'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// ─── 状态 ───
const isCollapsed = ref(false)
const routeRefreshing = ref(false)
const tagsViewRef = ref(null)

/** 当前激活的一级分组 key */
const activeGroupKey = computed(() => {
  // 控制台等独立页面不显示分组
  if (route.path === '/admin') return null
  const g = findGroupByPath(route.path)
  return g ? g.key : null
})

/** 当前分组的子菜单列表 */
const currentGroupChildren = computed(() => {
  if (!activeGroupKey.value) return []
  const g = menuGroups.find(g => g.key === activeGroupKey.value)
  return g ? g.children : []
})

/** 当前页面标题 */
const currentTitle = computed(() => {
  const metaTitle = route.meta?.title
  if (metaTitle) return metaTitle
  const item = findMenuItem(route.path)
  return item?.title || '管理后台'
})

/** keep-alive 缓存列表 */
const cachedViews = computed(() => {
  return tagsViewRef.value?.getVisitedNames?.() || []
})

// ─── 方法 ───

/** 切换一级分组 */
function switchGroup(group) {
  router.push(group.defaultPath)
}

/** 下拉命令 */
function handleCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/admin/settings')
  }
}

/** 刷新当前页面 */
async function handleRefresh() {
  routeRefreshing.value = true
  await new Promise(r => setTimeout(r, 0))
  await new Promise(r => setTimeout(r, 0))
  routeRefreshing.value = false
}

/** 返回用户端 */
function goToUser() {
  router.push('/')
}

onMounted(() => {
  if (!userStore.user) {
    userStore.getUserInfo()
  }
})
</script>

<style scoped>
.admin-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f7fa;
  min-width: 0;
  overflow: hidden;
}

/* ──────── 顶部一级导航 ──────── */
.top-nav {
  height: 56px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
  z-index: 100;
  min-width: 0;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 16px 6px 8px;
  cursor: pointer;
  color: #fff;
  flex-shrink: 0;
}

.logo-img {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  object-fit: cover;
}

.brand-text {
  font-size: 17px;
  font-weight: 700;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.group-nav {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: 4px;
}

.group-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  font-size: 13px;
  color: rgba(255,255,255,0.65);
  text-decoration: none;
  border-radius: 8px;
  transition: all .2s ease;
  white-space: nowrap;

  .el-icon { font-size: 15px; }

  &:hover {
    color: #fff;
    background: rgba(255,255,255,0.08);
  }

  &.active {
    color: #fff;
    background: rgba(74, 222, 128, 0.18);
    box-shadow: inset 0 -2px 0 0 #4ade80;
  }
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 8px;
  transition: background .2s;
}
.user-info:hover { background: rgba(255,255,255,0.08); }

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 12px;
}

.username {
  font-size: 13px;
  color: #fff;
}

/* ──────── 主内容区 ──────── */
.main-wrapper {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
  min-width: 0;
}

/* ──────── 左侧子菜单 ──────── */
.submenu-sidebar {
  width: 180px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow-y: auto;
}

.submenu-list {
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.submenu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  font-size: 13px;
  color: #555;
  text-decoration: none;
  border-radius: 8px;
  transition: all .18s ease;

  .el-icon {
    font-size: 16px;
    flex-shrink: 0;
    color: #888;
  }

  &:hover {
    color: #333;
    background: #f5f7fa;
    .el-icon { color: #4ade80; }
  }

  &.active {
    color: #16a34a;
    background: #f0fdf4;
    font-weight: 600;
    box-shadow: inset 3px 0 0 0 #16a34a;
    .el-icon { color: #16a34a; }
  }
}

/* ──────── 右侧内容区域 ──────── */
.content-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.topbar {
  height: 48px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
  min-width: 0;
}

.page-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  min-width: 0;
  min-height: 0;
}

/* ════════ 响应式 ════════ */

@media (max-width: 1200px) {
  .submenu-sidebar { width: 160px; }
  .group-item span { display: none; }
  .group-item { padding: 8px 12px; }
}

@media (max-width: 1024px) {
  .brand-text { display: none; }
  .submenu-sidebar { width: 56px; }
  .submenu-item span { display: none; }
  .submenu-item {
    justify-content: center; padding: 11px 0;
  }
  .submenu-item.active { box-shadow: none; background: #dcfce7; }
}

@media (max-width: 768px) {
  .admin-layout {
    display: block;
    padding-bottom: calc(64px + env(safe-area-inset-bottom));
  }
  .top-nav {
    position: fixed; top: 0; left: 0; right: 0;
    height: var(--header-height); z-index: var(--z-fixed);
  }
  .group-nav { gap: 0; }
  .group-item {
    padding: 8px 10px; font-size: 12px;
    span { display: none; }
  }
  .nav-right > .el-button:not(.theme-toggle):not(.lang-toggle) {
    display: inline-flex; width: 36px; height: 36px; padding: 0;
    font-size: 0;
  }
  .username { display: none; }
  .user-info { padding: 4px; }
  
  .main-wrapper {
    margin-top: var(--header-height);
    height: calc(100vh - var(--header-height) - 64px - env(safe-area-inset-bottom));
    flex-direction: column;
  }
  .submenu-sidebar {
    width: 100%; height: auto; max-height: 80px;
    border-right: none; border-bottom: 1px solid #e4e7ed;
  }
  .submenu-list {
    flex-direction: row;
    padding: 8px 12px;
    overflow-x: auto;
    gap: 6px;
  }
  .submenu-item {
    flex-shrink: 0; padding: 8px 12px;
    font-size: 12px; white-space: nowrap;
  }
  .submenu-item span { display: inline; }
  .content-area { overflow: hidden; }
  .content { padding: 16px; }
}

@media (max-width: 420px) {
  .nav-right :deep(.theme-toggle),
  .nav-right :deep(.lang-toggle) { display: none; }
}
</style>
