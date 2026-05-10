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
        <router-link 
          v-for="item in menuItems" 
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span v-if="!isCollapsed" class="nav-text">{{ item.label }}</span>
        </router-link>
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

      <!-- 内容区 -->
      <main class="content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores'
import {
  HomeFilled, User, Connection, List, Box, Guide,
  DArrowLeft, DArrowRight, ArrowDown, Tickets, Back, CreditCard,
  Share, Setting, Wallet, Coin
} from '@element-plus/icons-vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import LangToggle from '@/components/LangToggle.vue'
import logoSrc from '@/assets/image/logo.png'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isCollapsed = ref(false)

const menuItems = [
  { path: '/admin', label: '控制台', icon: markRaw(HomeFilled) },
  { path: '/admin/users', label: '用户管理', icon: markRaw(User) },
  { path: '/admin/card-management', label: '卡密管理', icon: markRaw(CreditCard) },
  { path: '/admin/recharge-management', label: '充值管理', icon: markRaw(Wallet) },
  { path: '/admin/billing-management', label: '账单管理', icon: markRaw(Wallet) },
  { path: '/admin/invite-management', label: '邀请返利', icon: markRaw(Share) },
  { path: '/admin/access-logs', label: '接口使用记录', icon: markRaw(List) },
  
  { path: '/admin/redis-management', label: 'Redis管理', icon: markRaw(Coin) },
  { path: '/admin/model-management', label: '模型管理', icon: markRaw(Box) },
  { path: '/admin/provider-management', label: '供应商管理', icon: markRaw(Connection) },
  { path: '/admin/channel-management', label: '渠道管理', icon: markRaw(Guide) },
  { path: '/admin/ticket-management', label: '工单管理', icon: markRaw(Tickets) },
  { path: '/admin/system-settings', label: '系统设置', icon: markRaw(Setting) },
]

const currentTitle = computed(() => {
  const item = menuItems.find(m => m.path === route.path)
  return item?.label || '管理后台'
})

const isActive = (path) => {
  if (path === '/admin') return route.path === '/admin'
  return route.path.startsWith(path)
}

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/admin/settings')
  }
}

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

/* 侧边栏 */
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

.logo-icon svg {
  width: 100%;
  height: 100%;
}

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

/* 导航菜单 */
.nav-menu {
  flex: 1;
  padding: 16px 8px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 4px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  transition: all 0.2s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.nav-item.active {
  background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
  color: #fff;
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

/* 侧边栏底部 */
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.collapse-btn {
  width: 100%;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* 主内容区 */
.main-wrapper {
  flex: 1;
  margin-left: 240px;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.3s ease;
  min-width: 0;
}

.sidebar.collapsed + .main-wrapper {
  margin-left: 64px;
}

/* 顶部栏 */
.topbar {
  height: 64px;
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
  .topbar-right{
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }
}

.page-title {
  font-size: 20px;
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

.user-info:hover {
  background: #f5f7fa;
}

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

/* 内容区 */
.content {
  flex: 1;
  padding: 24px;
  min-width: 0;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 1024px) {
  .sidebar {
    width: 72px;
  }

  .sidebar:not(.collapsed) .logo-text,
  .sidebar:not(.collapsed) .nav-text {
    display: none;
  }

  /* .sidebar:not(.collapsed) + .main-wrapper,
  .main-wrapper {
    margin-left: 72px;
  } */

  .logo,
  .sidebar-footer {
    padding: 16px;
  }

  .nav-item {
    justify-content: center;
    padding: 12px;
  }

  .topbar {
    padding-inline: 20px;
  }

  .content {
    padding: 20px;
  }
}

@media (max-width: 768px) {
  .admin-layout {
    display: block;
    padding-bottom: calc(72px + env(safe-area-inset-bottom));
  }

  .sidebar,
  .sidebar.collapsed {
    top: auto;
    bottom: 0;
    left: 0;
    width: 100%;
    height: calc(64px + env(safe-area-inset-bottom));
    padding-bottom: env(safe-area-inset-bottom);
    background: rgba(26, 26, 46, 0.97);
    z-index: var(--z-fixed);
  }

  .logo,
  .sidebar-footer {
    display: none;
  }

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

  .nav-item {
    flex: 0 0 48px;
    width: 48px;
    height: 48px;
    justify-content: center;
    margin: 0;
    padding: 0;
  }

  .nav-text {
    display: none;
  }

  .sidebar + .main-wrapper,
  .sidebar.collapsed + .main-wrapper,
  .main-wrapper {
    margin-left: 0;
  }

  .topbar {
    height: var(--header-height);
    width: 100vw;
    padding-inline: var(--space-3);
  }

  .page-title {
    max-width: 42vw;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 18px;
  }

  .topbar-right {
    gap: 8px;
  }

  .topbar-right > .el-button {
    display: inline-flex;
    width: 40px;
    height: 40px;
    padding: 0;
    font-size: 0;
    justify-content: center;
    flex-shrink: 0;
  }

  .topbar-right > .el-button .el-icon {
    margin: 0;
    font-size: 18px;
  }

  .username {
    display: none;
  }

  .user-info {
    padding: 4px;
  }

  .content {
    padding: var(--space-4);
  }
}

@media (max-width: 420px) {
  .topbar :deep(.theme-toggle),
  .topbar :deep(.lang-toggle) {
    display: none;
  }
}
</style>
