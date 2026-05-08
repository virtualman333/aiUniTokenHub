<template>
  <div class="user-layout">
    <!-- 顶部导航 -->
    <header class="topbar">
      <div class="topbar-left">
        <router-link to="/" class="logo">
          <img :src="logoSrc" alt="logo" class="logo-img" />
          <span class="logo-text">uniTokenHub</span>
        </router-link>
      </div>

      <nav class="nav-menu">
        <router-link 
          v-for="item in navItems" 
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="topbar-right">
        <ThemeToggle />
        <LangToggle />
        <el-button v-if="isAdmin" type="primary" @click="goToAdmin">
          <el-icon><Setting /></el-icon> 进入管理端
        </el-button>
        <el-dropdown @command="handleCommand">
          <div class="user-info">
            <div class="avatar">{{ userStore.user?.username?.[0]?.toUpperCase() || 'U' }}</div>
            <div class="user-detail">
              <span class="username">{{ userStore.user?.username }}</span>
              <span class="balance">¥{{ Number(userStore.user?.balance || 0).toFixed(4) }}</span>
            </div>
            <el-icon><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="settings">
                <el-icon><Setting /></el-icon> 账户设置
              </el-dropdown-item>
              <el-dropdown-item command="billing">
                <el-icon><Wallet /></el-icon> 账单中心
              </el-dropdown-item>
              <el-dropdown-item command="keys">
                <el-icon><Key /></el-icon> 我的密钥
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon> 退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 主内容区 -->
    <div class="main-wrapper">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores'
import {
  HomeFilled, Document, Box, List, Setting, Wallet, Key, 
  ArrowDown, SwitchButton, Tickets, ChatRound
} from '@element-plus/icons-vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import LangToggle from '@/components/LangToggle.vue'
import logoSrc from '@/assets/image/logo.png'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isAdmin = computed(() => userStore.user?.role === 'admin')

const navItems = [
  { path: '/', label: '控制台', icon: markRaw(HomeFilled) },
  { path: '/api-doc', label: '接口文档', icon: markRaw(Document) },
  { path: '/model-square', label: '模型广场', icon: markRaw(Box) },
  { path: '/chat', label: 'AI 对话', icon: markRaw(ChatRound) },
  { path: '/usage-log', label: '使用记录', icon: markRaw(List) },
  { path: '/tickets', label: '工单中心', icon: markRaw(Tickets) },
]

onMounted(() => {
  if (!userStore.user) {
    userStore.getUserInfo()
  }
})

const isActive = (path) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (command === 'settings') {
    router.push('/settings')
  } else if (command === 'billing') {
    router.push('/billing')
  } else if (command === 'keys') {
    router.push('/my-keys')
  }
}

const goToAdmin = () => {
  router.push('/admin')
}
</script>

<style scoped>
.user-layout {
  min-height: 100vh;
  background: var(--bg-secondary);
}

/* 顶部导航 */
.topbar {
  height: var(--header-height);
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  padding: 0 var(--space-6);
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  background: rgba(255, 255, 255, 0.9);
  min-width: 0;
}

.topbar-left {
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  text-decoration: none;
  transition: transform var(--transition-fast);
  
  &:hover {
    transform: scale(1.02);
  }
}

.logo-img {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  object-fit: cover;
  box-shadow: var(--shadow-sm);
}

.logo-text {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 导航菜单 */
.nav-menu {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-left: var(--space-12);
  min-width: 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-lg);
  text-decoration: none;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  position: relative;
  
  &::after {
    content: '';
    position: absolute;
    bottom: -2px;
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 2px;
    background: var(--primary-500);
    border-radius: var(--radius-full);
    transition: width var(--transition-fast);
  }
  
  &:hover {
    background: var(--primary-50);
    color: var(--primary-700);
    
    &::after {
      width: 60%;
    }
  }
  
  &.active {
    background: var(--primary-50);
    color: var(--primary-700);
    font-weight: var(--font-semibold);
    
    &::after {
      width: 80%;
    }
  }
}

.nav-item .el-icon {
  font-size: 18px;
}

/* 用户信息 */
.topbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
  
  &:hover {
    background: var(--neutral-50);
    border-color: var(--border-light);
  }
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  background: var(--gradient-primary);
  color: var(--text-inverse);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-semibold);
  font-size: var(--text-sm);
  box-shadow: var(--shadow-sm);
}

.user-detail {
  display: flex;
  flex-direction: column;
}

.username {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.balance {
  font-size: var(--text-xs);
  color: var(--success-600);
  font-weight: var(--font-semibold);
}

/* 主内容区 */
.main-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-6);
  animation: fadeIn 0.3s ease-out;
  min-width: 0;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base), transform var(--transition-base);
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media (max-width: 1200px) {
  .nav-menu {
    margin-left: var(--space-6);
  }

  .nav-item {
    padding-inline: var(--space-3);
  }

  .topbar-right {
    gap: var(--space-2);
  }
}

@media (max-width: 980px) {
  .topbar {
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }

  .logo-text {
    display: none;
  }

  .nav-menu {
    position: fixed;
    left: 50%;
    right: auto;
    bottom: max(var(--space-3), env(safe-area-inset-bottom));
    transform: translateX(-50%);
    width: min(calc(100vw - 24px), 520px);
    height: 64px;
    margin: 0;
    padding: var(--space-2);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-xl);
    background: rgba(255, 255, 255, 0.96);
    box-shadow: var(--shadow-lg);
    justify-content: space-evenly;
    gap: 0;
    overflow: hidden;
    z-index: var(--z-fixed);
  }

  .nav-item span {
    display: none;
  }

  .nav-item {
    flex: 1 1 0;
    width: auto;
    min-width: 48px;
    max-width: 64px;
    height: 48px;
    justify-content: center;
    padding: 0;
  }

  .nav-item .el-icon {
    font-size: 22px;
  }

  .main-wrapper {
    padding-bottom: calc(88px + env(safe-area-inset-bottom));
  }
}

@media (max-width: 768px) {
  .nav-menu {
    left: 50%;
    right: auto;
    bottom: max(var(--space-3), env(safe-area-inset-bottom));
    transform: translateX(-50%);
    width: min(calc(100vw - 24px), 520px);
    height: 64px;
    margin: 0;
    padding: var(--space-2);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-xl);
    background: rgba(255, 255, 255, 0.96);
    box-shadow: var(--shadow-lg);
    justify-content: space-evenly;
    gap: 0;
    overflow: hidden;
    z-index: var(--z-fixed);
  }

  .nav-item {
    flex: 1 1 0;
    width: auto;
    min-width: 48px;
    max-width: 64px;
    height: 48px;
  }
  
  .user-detail {
    display: none;
  }
  
  .topbar {
    padding: 0 var(--space-3);
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

  .user-info {
    padding: var(--space-1);
    gap: var(--space-1);
  }

  .avatar {
    width: 36px;
    height: 36px;
  }
  
  .main-wrapper {
    padding: var(--space-4);
    padding-bottom: calc(88px + env(safe-area-inset-bottom));
  }
}

@media (max-width: 420px) {
  .topbar :deep(.theme-toggle),
  .topbar :deep(.lang-toggle) {
    display: none;
  }
}
</style>
