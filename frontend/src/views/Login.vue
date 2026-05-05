<template>
  <div class="login-page">
    <div class="login-container">
      <!-- 左侧品牌区域 -->
      <div class="brand-section">
        <div class="brand-content">
          <div class="logo">
            <svg viewBox="0 0 48 48" fill="none">
              <rect x="4" y="4" width="40" height="40" rx="8" fill="url(#logoGradient)"/>
              <path d="M24 12L12 20l12 8 12-8-12-8z" fill="#fff" opacity="0.9"/>
              <path d="M12 28l12 8 12-8" stroke="#fff" stroke-width="2" opacity="0.7"/>
              <path d="M12 24l12 8 12-8" stroke="#fff" stroke-width="2" opacity="0.5"/>
              <defs>
                <linearGradient id="logoGradient" x1="4" y1="4" x2="44" y2="44">
                  <stop stop-color="#4ade80"/>
                  <stop offset="1" stop-color="#22c55e"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1 class="brand-title">uniTokenHub</h1>
          <p class="brand-subtitle">统一Token中转服务</p>
          
          <div class="features">
            <div class="feature">
              <el-icon><Link /></el-icon>
              <span>多渠道聚合</span>
            </div>
            <div class="feature">
              <el-icon><TrendCharts /></el-icon>
              <span>智能负载均衡</span>
            </div>
            <div class="feature">
              <el-icon><Coin /></el-icon>
              <span>透明计费</span>
            </div>
          </div>
        </div>
        
        <div class="brand-decoration">
          <div class="circle circle-1"></div>
          <div class="circle circle-2"></div>
          <div class="circle circle-3"></div>
        </div>
      </div>

      <!-- 右侧登录区域 -->
      <div class="form-section">
        <div class="form-container">
          <div class="form-header">
            <h2>欢迎回来</h2>
            <p>登录到您的账户</p>
          </div>

          <el-form 
            ref="formRef"
            :model="loginForm" 
            :rules="rules" 
            class="login-form"
            @submit.prevent="handleLogin"
          >
            <el-form-item prop="username">
              <el-input 
                v-model="loginForm.username" 
                placeholder="用户名"
                size="large"
                :prefix-icon="User"
              />
            </el-form-item>
            
            <el-form-item prop="password">
              <el-input 
                v-model="loginForm.password" 
                type="password"
                placeholder="密码"
                size="large"
                :prefix-icon="Lock"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <div class="form-options">
              <el-checkbox v-model="rememberMe">记住我</el-checkbox>
              <el-link type="primary">忘记密码？</el-link>
            </div>

            <el-button 
              type="primary" 
              size="large" 
              :loading="loading" 
              class="login-btn"
              @click="handleLogin"
            >
              登录
            </el-button>
          </el-form>

          <div class="form-footer">
            <span>还没有账户？</span>
            <el-link type="primary" @click="$router.push('/register')">立即注册</el-link>
          </div>

          <!-- 测试账号提示 -->
          <div class="test-accounts">
            <div class="test-title">测试账号</div>
            <div class="test-accounts-grid">
              <div class="test-account" @click="fillTest('admin')">
                <span class="role">管理员</span>
                <code>admin / admin123</code>
              </div>
              <div class="test-account" @click="fillTest('testuser')">
                <span class="role">用户</span>
                <code>testuser / test123</code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores'
import { ElMessage } from 'element-plus'
import { User, Lock, Link, TrendCharts, Coin } from '@element-plus/icons-vue'
import Cookies from 'js-cookie'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)
const rememberMe = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const fillTest = (type) => {
  if (type === 'admin') {
    loginForm.username = 'admin'
    loginForm.password = 'admin123'
  } else {
    loginForm.username = 'testuser'
    loginForm.password = 'test123'
  }
}

const handleLogin = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    
    // 根据角色跳转
    const role = Cookies.get('userRole')
    router.push(role === 'admin' ? '/admin' : '/')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-container {
  display: flex;
  background: #fff;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  max-width: 1000px;
  width: 100%;
}

/* 左侧品牌区域 */
.brand-section {
  flex: 1;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
  padding: 48px;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.brand-content {
  position: relative;
  z-index: 1;
}

.logo {
  width: 72px;
  height: 72px;
  margin-bottom: 24px;
}

.logo svg {
  width: 100%;
  height: 100%;
}

.brand-title {
  font-size: 36px;
  font-weight: 700;
  margin: 0 0 8px;
}

.brand-subtitle {
  font-size: 18px;
  opacity: 0.8;
  margin: 0 0 48px;
}

.features {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
}

.feature .el-icon {
  font-size: 24px;
  color: #4ade80;
}

/* 装饰圆圈 */
.brand-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.circle {
  position: absolute;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(74, 222, 128, 0.2), rgba(34, 197, 94, 0.1));
}

.circle-1 {
  width: 200px;
  height: 200px;
  top: -50px;
  right: -50px;
}

.circle-2 {
  width: 150px;
  height: 150px;
  bottom: 100px;
  left: -30px;
}

.circle-3 {
  width: 100px;
  height: 100px;
  bottom: -30px;
  right: 50px;
}

/* 右侧表单区域 */
.form-section {
  flex: 1;
  padding: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-container {
  width: 100%;
  max-width: 360px;
}

.form-header {
  margin-bottom: 32px;
  text-align: center;
}

.form-header h2 {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 8px;
}

.form-header p {
  color: #6b7280;
  margin: 0;
}

.login-form {
  margin-bottom: 24px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.login-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  border-radius: 8px;
}

.form-footer {
  text-align: center;
  color: #6b7280;
  margin-bottom: 24px;
}

/* 测试账号 */
.test-accounts {
  background: #f9fafb;
  border-radius: 12px;
  padding: 16px;
}

.test-title {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.test-accounts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.test-account {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.test-account:hover {
  border-color: #4ade80;
  background: #f0fdf4;
}

.test-account .role {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 2px;
}

.test-account code {
  font-size: 12px;
  color: #1f2937;
}

@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
  }
  
  .brand-section {
    padding: 32px;
  }
  
  .features {
    display: none;
  }
  
  .form-section {
    padding: 32px;
  }
}
</style>
