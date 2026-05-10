<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="logo">
        <div class="logo-icon">
          <img :src="logoSrc" alt="logo" class="logo-img" />
        </div>
        <span v-if="!isCollapsed" class="logo-text">uniTokenHub</span>
      </div>

      <nav class="nav-menu">
        <template v-for="item in menuConfig" :key="item.path || item.title">
          <!-- 分组标题 -->
          <div
            v-if="item.type === 'group'"
            class="group-title"
            :class="{ collapsed: isCollapsed }"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span v-if="!isCollapsed">{{ item.title }}</span>
            <div v-if="!isCollapsed" class="group-line"></div>
          </div>

          <!-- 可导航菜单项 -->
          <router-link
            v-else-if="!item.hidden"
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item.path) }"
            :title="isCollapsed ? item.title : ''"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span v-if="!isCollapsed" class="nav-text">{{ item.title }}</span>
          </router-link>
        </template>
      </nav>

      <div class="sidebar-footer">
        <el-button class="collapse-btn" @click="isCollapsed = !isCollapsed">
          <el-icon v-if="!isCollapsed"><DArrowLeft /></el-icon>
          <el-icon v-else><DArrowRight /></el-icon>
        </el-button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-wrapper">
      <!-- 顶部栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <h1 class="page-title">{{ currentTitle }}</h1>
        </div>
        <div class="topbar-right">
          <ThemeToggle />
          <LangToggle />
          <el-button @click="goToUser" text>
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

      <!-- 多标签页 -->
      <TagsView ref="tagsViewRef" @refresh="handleRefresh" />

      <!-- 内容区（无过渡闪烁，keep-alive 缓存已访问页面） -->
      <main class="content">
        <router-view v-slot="{ Component, route: curRoute }">
          <keep-alive :include="cachedViews">
            <component :is="Component" v-if="curRoute.path && !routeRefreshing" :key="curRoute.name || curRoute.path" />
          </keep-alive>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores'
import {
  DArrowLeft, DArrowRight, ArrowDown, Back
} from '@element-plus/icons-vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import LangToggle from '@/components/LangToggle.vue'
import TagsView from '@/components/admin/TagsView.vue'
import { adminMenu, findMenuItem } from '@/config/adminMenu'
import logoSrc from '@/assets/image/logo.png'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// ─── 状态 ───
const isCollapsed = ref(false)
const routeRefreshing = ref(false)
const tagsViewRef = ref(null)

/** 菜单配置 */
const menuConfig = adminMenu

/** 当前页面标题（优先从 meta，其次菜单配置） */
const currentTitle = computed(() => {
  const metaTitle = route.meta?.title
  if (metaTitle) return metaTitle
  const item = findMenuItem(route.path)
  return item?.title || '管理后台'
})

/** keep-alive 缓存列表：从标签页组件获取已访问路由名 */
const cachedViews = computed(() => {
  return tagsViewRef.value?.getVisitedNames?.() || []
})

// ─── 方法 ───

/** 判断菜单是否激活 */
const isActive = (path) => {
  if (path === '/admin') return route.path === '/admin'
  return route.path.startsWith(path)
}

/** 下拉命令 */
const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/admin/settings')
  }
}

/** 刷新当前页面 */
const handleRefresh = async () => {
  routeRefreshing.value = true
  await nextTick()
  await nextTick()
  routeRefreshing.value = false
}

/** 返回用户端 */
const goToUser = () => {
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
  min-height: 100vh;
  background: #f5f7fa;
  min-width: 0;
}

/* ──────── 侧边栏 ──────── */
.sidebar {
  width: 240px;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  position: fixed;
  height: 100vh;
  z-index: 100;
}

.sidebar.collapsed {
  width: 64px;
}

.logo {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-icon {
  width: 32px;
  height: 32px;
  color: #4ade80;
  flex-shrink: 0;
}
.logo-icon svg { width: 100%; height: 100%; }

.logo-img {
  width: 100%;
  height: 100%;
  border-radius: 8px;
  object-fit: cover;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
}

/* ──────── 分组导航菜单 ──────── */
.nav-menu {
  flex: 1;
  padding: 8px;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 分组标题 */
.group-title {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 12px 6px;
  font-size: 11px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.35);
  text-transform: uppercase;
  letter-spacing: 1px;
  white-space: nowrap;
  position: relative;

  &.collapsed {
    justify-content: center;
    padding: 16px 0 4px;
    .group-line { display: none; }
    span { display: none; }
  }

  .el-icon {
    font-size: 13px;
    flex-shrink: 0;
  }
}

.group-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(255,255,255,0.15), transparent);
}

/* 导航项 */
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  margin-bottom: 2px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  transition: all 0.2s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.nav-item.active {
  background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(74, 222, 128, 0.25);
}

.nav-item .el-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-text {
  font-size: 14px;
  white-space: nowrap;
}

/* ──────── 侧边栏底部 ──────── */
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.collapse-btn {
  width: 100%;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  &:hover { background: rgba(255, 255, 255, 0.18); }
}

/* ──────── 主内容区 ──────── */
.main-wrapper {
  flex: 1;
  margin-left: 240px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left 0.3s ease;
  min-width: 0;
}

.sidebar.collapsed + .main-wrapper {
  margin-left: 64px;
}

/* ──────── 顶部栏 ──────── */
.topbar {
  height: 56px;
  width: 100%;
  box-sizing: border-box;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 50;
  min-width: 0;
  flex-shrink: 0;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  transition: background 0.2s;
}
.user-info:hover { background: #f5f7fa; }

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
}

.username {
  font-size: 14px;
  color: #374151;
}

/* ──────── 内容区 ──────── */
.content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  min-width: 0;
}

/* ════════ 响应式 ════════ */

@media (max-width: 1024px) {
  .sidebar {
    width: 72px;
  }
  .sidebar:not(.collapsed) .logo-text,
  .sidebar:not(.collapsed) .nav-text,
  .sidebar:not(.collapsed) .group-title span,
  .sidebar:not(.collapsed) .group-line {
    display: none;
  }
  .sidebar:not(.collapsed) .group-title {
    justify-content: center;
    padding: 16px 0 4px;
  }
  .nav-item { justify-content: center; padding: 12px; }
  .topbar { padding-inline: 20px; }
  .content { padding: 20px; }
}

@media (max-width: 768px) {
  .admin-layout {
    display: block;
    padding-bottom: calc(72px + env(safe-area-inset-bottom));
  }
  .sidebar, .sidebar.collapsed {
    top: auto;
    bottom: 0;
    left: 0;
    width: 100%;
    height: calc(64px + env(safe-area-inset-bottom));
    padding-bottom: env(safe-area-inset-bottom);
    background: rgba(26, 26, 46, 0.97);
    z-index: var(--z-fixed);
  }
  .logo, .sidebar-footer { display: none; }
  .nav-menu {
    flex: none;
    display: flex;
    gap: 6px;
    height: 64px;
    padding: 8px;
    overflow-x: auto;
    overflow-y: hidden;
    overscroll-behavior-x: contain;
  }
  .group-title { display: none; }
  .nav-item {
    flex: 0 0 48px; width: 48px; height: 48px;
    justify-content: center; margin: 0; padding: 0;
  }
  .nav-text { display: none; }

  .sidebar + .main-wrapper,
  .sidebar.collapsed + .main-wrapper,
  .main-wrapper { margin-left: 0; }

  .topbar {
    height: var(--header-height); width: 100vw; padding-inline: var(--space-3);
  }
  .page-title {
    max-width: 42vw; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; font-size: 18px;
  }
  .topbar-right { gap: 8px; }
  .topbar-right > .el-button {
    display: inline-flex; width: 40px; height: 40px; padding: 0;
    font-size: 0; justify-content: center; flex-shrink: 0;
  }
  .topbar-right > .el-button .el-icon { margin: 0; font-size: 18px; }
  .username { display: none; }
  .user-info { padding: 4px; }
  .content { padding: var(--space-4); }
}

@media (max-width: 420px) {
  .topbar :deep(.theme-toggle),
  .topbar :deep(.lang-toggle) { display: none; }
}
</style>
