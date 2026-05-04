<template>
  <div class="user-layout">
    <!-- 顶部导航 -->
    <header class="topbar">
      <div class="topbar-left">
        <router-link to="/" class="logo">
          <svg viewBox="0 0 48 48" fill="none">
            <rect x="4" y="4" width="40" height="40" rx="8" fill="url(#logoGrad)"/>
            <path d="M24 12L12 20l12 8 12-8-12-8z" fill="#fff" opacity="0.9"/>
            <path d="M12 28l12 8 12-8" stroke="#fff" stroke-width="2" opacity="0.7"/>
            <path d="M12 24l12 8 12-8" stroke="#fff" stroke-width="2" opacity="0.5"/>
            <defs>
              <linearGradient id="logoGrad" x1="4" y1="4" x2="44" y2="44">
                <stop stop-color="#4ade80"/>
                <stop offset="1" stop-color="#22c55e"/>
              </linearGradient>
            </defs>
          </svg>
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
        <el-dropdown @command="handleCommand">
          <div class="user-info">
            <div class="avatar">{{ userStore.user?.username?.[0]?.toUpperCase() || 'U' }}</div>
            <div class="user-detail">
              <span class="username">{{ userStore.user?.username }}</span>
              <span class="balance">¥{{ (userStore.user?.balance || 0).toFixed(2) }}</span>
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
  HomeFilled, Connection, Box, List, Setting, Wallet, Key, 
  ArrowDown, SwitchButton
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const navItems = [
  { path: '/', label: '控制台', icon: markRaw(HomeFilled) },
  { path: '/api-list', label: 'API列表', icon: markRaw(Connection) },
  { path: '/model-square', label: '模型广场', icon: markRaw(Box) },
  { path: '/usage-log', label: '使用记录', icon: markRaw(List) },
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
</script>

<style scoped>
.user-layout {
  min-height: 100vh;
  background: #f8fafc;
}

/* 顶部导航 */
.topbar {
  height: 64px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.topbar-left {
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
}

.logo svg {
  width: 36px;
  height: 36px;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

/* 导航菜单 */
.nav-menu {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 48px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  text-decoration: none;
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.nav-item:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.nav-item.active {
  background: #ecfdf5;
  color: #059669;
}

.nav-item .el-icon {
  font-size: 18px;
}

/* 用户信息 */
.topbar-right {
  margin-left: auto;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.user-info:hover {
  background: #f3f4f6;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
}

.user-detail {
  display: flex;
  flex-direction: column;
}

.username {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
}

.balance {
  font-size: 12px;
  color: #059669;
  font-weight: 600;
}

/* 主内容区 */
.main-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
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

@media (max-width: 768px) {
  .nav-menu {
    display: none;
  }
  
  .user-detail {
    display: none;
  }
}
</style>
