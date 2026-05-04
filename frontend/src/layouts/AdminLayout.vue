<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <el-icon><Setting /></el-icon>
        <span>管理后台</span>
      </div>
      <el-menu
        :default-active="route.path"
        router
        class="sidebar-menu"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/admin">
          <el-icon><DataAnalysis /></el-icon>
          <span>总览</span>
        </el-menu-item>
        <el-menu-item index="/admin/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/api-management">
          <el-icon><Connection /></el-icon>
          <span>API管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/api-categories">
          <el-icon><FolderOpened /></el-icon>
          <span>API分类</span>
        </el-menu-item>
        <el-menu-item index="/admin/access-logs">
          <el-icon><Document /></el-icon>
          <span>访问日志</span>
        </el-menu-item>
        <el-divider style="margin: 10px 0; border-color: #3d4a5a;" />
        <el-menu-item index="/">
          <el-icon><Back /></el-icon>
          <span>返回用户端</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/admin' }">管理后台</el-breadcrumb-item>
            <el-breadcrumb-item>{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :src="userStore.user?.avatar">
                {{ userStore.user?.username?.[0]?.toUpperCase() }}
              </el-avatar>
              <span class="username">{{ userStore.user?.username }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人资料</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

onMounted(async () => {
  if (userStore.isLoggedIn && !userStore.user) {
    await userStore.getUserInfo()
  }
})

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style lang="scss" scoped>
.layout-container {
  height: 100%;
}

.sidebar {
  background: #304156;
  
  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    padding: 0 20px;
    color: #fff;
    font-size: 18px;
    font-weight: bold;
    border-bottom: 1px solid #3d4a5a;
    
    .el-icon {
      margin-right: 10px;
      font-size: 24px;
    }
  }
  
  .sidebar-menu {
    border-right: none;
  }
}

.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  
  .user-info {
    display: flex;
    align-items: center;
    cursor: pointer;
    
    .username {
      margin-left: 10px;
    }
  }
}

.main-content {
  background: #f5f7fa;
  overflow-y: auto;
}
</style>
