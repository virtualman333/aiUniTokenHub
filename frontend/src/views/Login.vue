<template>
  <div class="login-page">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="navbar-container">
        <div class="navbar-brand">
          <img :src="logoSrc" alt="uniTokenHub" class="logo" />
          <span class="brand-name">uniTokenHub</span>
        </div>
        <div class="navbar-links">
          <a href="/#features" class="nav-link">{{ t('home.nav.features') }}</a>
          <a href="/#pricing" class="nav-link">{{ t('home.nav.pricing') }}</a>
          <a href="/#docs" class="nav-link">{{ t('home.nav.docs') }}</a>
        </div>
        <div class="navbar-actions">
          <button class="btn btn-outline" @click="$router.push('/login')">{{ t('auth.login') }}</button>
          <button class="btn btn-primary" @click="$router.push('/register')">{{ t('auth.register') }}</button>
        </div>
      </div>
    </nav>
    
    <div class="login-container">
      <!-- 左侧品牌区域 -->
      <div class="brand-section">
        <div class="brand-content">
          <div class="logo">
            <img :src="logoSrc" alt="logo" class="logo-img" />
          </div>
          <h1 class="brand-title">{{ t('brand.title') }}</h1>
          <p class="brand-subtitle">{{ t('brand.subtitle') }}</p>
          
          <div class="features">
            <div class="feature">
              <el-icon><Link /></el-icon>
              <span>{{ t('brand.multiChannel') }}</span>
            </div>
            <div class="feature">
              <el-icon><TrendCharts /></el-icon>
              <span>{{ t('brand.loadBalance') }}</span>
            </div>
            <div class="feature">
              <el-icon><Coin /></el-icon>
              <span>{{ t('brand.transparentBilling') }}</span>
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
            <h2>{{ t('auth.welcomeBack') }}</h2>
            <p>{{ t('auth.loginToAccount') }}</p>
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
                :placeholder="t('auth.username')"
                size="large"
                :prefix-icon="User"
              />
            </el-form-item>
            
            <el-form-item prop="password">
              <el-input 
                v-model="loginForm.password" 
                type="password"
                :placeholder="t('auth.password')"
                size="large"
                :prefix-icon="Lock"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <div class="form-options">
              <el-checkbox v-model="rememberMe">{{ t('auth.rememberMe') }}</el-checkbox>
              <router-link to="/forgot-password" class="forgot-link">{{ t('auth.forgotPassword') }}</router-link>
            </div>

            <el-button 
              type="primary" 
              size="large" 
              :loading="loading" 
              class="login-btn"
              @click="handleLogin"
            >
              {{ t('auth.login') }}
            </el-button>
          </el-form>

          <div class="form-footer">
            <span>{{ t('auth.noAccount') }}</span>
            <el-link type="primary" @click="$router.push('/register')">{{ t('auth.signUpNow') }}</el-link>
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
import { useI18n } from '@/composables/useI18n'
import { ElMessage } from 'element-plus'
import { User, Lock, Link, TrendCharts, Coin } from '@element-plus/icons-vue'
import Cookies from 'js-cookie'
import logoSrc from '@/assets/image/logo.png'

const { t } = useI18n()
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
  username: [{ required: true, message: t('auth.pleaseInputUsername'), trigger: 'blur' }],
  password: [{ required: true, message: t('auth.pleaseInputPassword'), trigger: 'blur' }]
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
    ElMessage.success(t('auth.loginSuccess'))
    router.push('/app')
  } catch (error) {
    ElMessage.error(error.message || t('auth.loginFailed'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.navbar-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.navbar-brand .logo {
  width: 36px;
  height: 36px;
  border-radius: 8px;
}

.brand-name {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
}

.navbar-links {
  display: flex;
  gap: 32px;
}

.nav-link {
  text-decoration: none;
  color: #606266;
  font-weight: 500;
  transition: color 0.3s;
  
  &:hover {
    color: #409eff;
  }
}

.navbar-actions {
  display: flex;
  gap: 10px;
}

.btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  border: none;
  font-size: 14px;
}

.btn-outline {
  background: transparent;
  border: 1px solid #dcdfe6;
  color: #606266;
  
  &:hover {
    border-color: #409eff;
    color: #409eff;
  }
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }
}

.login-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  padding-top: 80px;
}

.login-container {
  display: flex;
  background: #fff;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  max-width: 1000px;
  width: 100%;
  min-width: 0;
}

/* 深色主题适配 */
html.dark .login-container {
  background: #252525;
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
}

.logo-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
}

.brand-title {
  color: #fff;
  font-size: 36px;
  font-weight: 700;
  margin: 0 0 8px;
}

.brand-subtitle {
  font-size: 18px;
  color: #fff;
  opacity: 0.7;
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
  background: var(--bg-card);
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
  color: var(--text-primary);
  margin: 0 0 8px;
}

.form-header p {
  color: var(--text-secondary);
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
  color: var(--text-secondary);
  margin-bottom: 24px;
}

@media (max-width: 768px) {
  .login-page {
    align-items: flex-start;
    padding: 16px;
  }

  .login-container {
    flex-direction: column;
    border-radius: 18px;
  }
  
  .brand-section {
    padding: 28px;
  }

  .logo {
    width: 56px;
    height: 56px;
    margin-bottom: 16px;
  }

  .brand-title {
    font-size: 28px;
  }

  .brand-subtitle {
    font-size: 15px;
    margin-bottom: 0;
  }
  
  .features {
    display: none;
  }
  
  .form-section {
    padding: 28px;
  }

  .form-header {
    margin-bottom: 24px;
  }

  .form-header h2 {
    font-size: 24px;
  }
}

@media (max-width: 420px) {
  .login-page {
    padding: 10px;
  }

  .brand-section,
  .form-section {
    padding: 22px 18px;
  }

  .form-options {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }
}
</style>
