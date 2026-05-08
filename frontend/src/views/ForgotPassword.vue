<template>
  <div class="forgot-password-page">
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
    
    <div class="forgot-password-container">
      <div class="forgot-password-box">
        <div class="forgot-password-header">
          <div class="icon-wrapper">
            <el-icon class="icon"><Key /></el-icon>
          </div>
          <h2>{{ t('auth.forgotPassword') }}</h2>
          <p>{{ t('auth.forgotPasswordDesc') }}</p>
        </div>
        
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          class="forgot-password-form"
          @submit.prevent="handleSubmit"
        >
          <el-form-item prop="email" v-if="step === 1">
            <el-input
              v-model="form.email"
              :placeholder="t('auth.email')"
              size="large"
              :prefix-icon="Message"
            />
          </el-form-item>
          
          <el-form-item prop="email_code" v-if="step === 2">
            <div class="code-row">
              <el-input
                v-model="form.email_code"
                :placeholder="t('auth.emailCode')"
                size="large"
                :prefix-icon="Key"
                maxlength="6"
              />
              <el-button
                type="primary"
                size="large"
                class="code-btn"
                :disabled="codeBtnDisabled"
                :loading="sendingCode"
                @click="handleSendCode"
              >
                {{ codeBtnText }}
              </el-button>
            </div>
          </el-form-item>
          
          <el-form-item prop="password" v-if="step === 2">
            <el-input
              v-model="form.password"
              type="password"
              :placeholder="t('auth.newPassword')"
              size="large"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          
          <el-form-item prop="password_confirm" v-if="step === 2">
            <el-input
              v-model="form.password_confirm"
              type="password"
              :placeholder="t('auth.confirmPassword')"
              size="large"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="handleSubmit"
            />
          </el-form-item>
          
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              class="submit-btn"
              @click="handleSubmit"
            >
              {{ step === 1 ? t('auth.sendCode') : t('auth.resetPassword') }}
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="forgot-password-footer">
          <router-link to="/login">{{ t('auth.backToLogin') }}</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Key, Message, Lock } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'
import { useUserStore } from '@/stores'
import logoSrc from '@/assets/image/logo.png'

const router = useRouter()
const { t } = useI18n()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)
const sendingCode = ref(false)
const countdown = ref(0)
let timer = null
const step = ref(1) // 1: 输入邮箱, 2: 输入验证码和新密码

const form = reactive({
  email: '',
  email_code: '',
  password: '',
  password_confirm: ''
})

const validatePasswordConfirm = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error(t('auth.passwordNotMatch')))
  } else {
    callback()
  }
}

const rules = {
  email: [
    { required: true, message: t('auth.enterEmail'), trigger: 'blur' },
    { type: 'email', message: t('auth.invalidEmail'), trigger: 'blur' }
  ],
  email_code: [
    { required: true, message: t('auth.enterCode'), trigger: 'blur' },
    { len: 6, message: t('auth.codeLength'), trigger: 'blur' }
  ],
  password: [
    { required: true, message: t('auth.enterPassword'), trigger: 'blur' },
    { min: 6, message: t('auth.passwordLength'), trigger: 'blur' }
  ],
  password_confirm: [
    { required: true, message: t('auth.confirmPassword'), trigger: 'blur' },
    { validator: validatePasswordConfirm, trigger: 'blur' }
  ]
}

const codeBtnDisabled = computed(() => sendingCode.value || countdown.value > 0)
const codeBtnText = computed(() => {
  if (countdown.value > 0) return `${countdown.value}s ${t('auth.resend')}`
  return t('auth.getCode')
})

function startCountdown(seconds) {
  countdown.value = seconds
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    if (countdown.value > 0) {
      countdown.value--
    } else {
      clearInterval(timer)
    }
  }, 1000)
}

const handleSendCode = async () => {
  if (!form.email) {
    ElMessage.error(t('auth.enterEmail'))
    return
  }
  
  sendingCode.value = true
  try {
    await userStore.sendResetCode(form.email)
    ElMessage.success(t('auth.codeSent'))
    startCountdown(60)
  } catch (error) {
    ElMessage.error(error.message || t('auth.sendCodeFailed'))
  } finally {
    sendingCode.value = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value.validate()) return
  
  loading.value = true
  try {
    if (step.value === 1) {
      await userStore.sendResetCode(form.email)
      ElMessage.success(t('auth.codeSent'))
      step.value = 2
      startCountdown(60)
    } else {
      await userStore.resetPassword(form.email, form.email_code, form.password)
      ElMessage.success(t('auth.passwordResetSuccess'))
      router.push('/login')
    }
  } catch (error) {
    ElMessage.error(error.message || (step.value === 1 ? t('auth.sendCodeFailed') : t('auth.resetFailed')))
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
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
  padding: 12px 24px;
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
  width: 32px;
  height: 32px;
  border-radius: 8px;
}

.brand-name {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
}

.navbar-links {
  display: flex;
  gap: 28px;
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
  padding: 7px 18px;
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

.forgot-password-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.forgot-password-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  padding-top: 100px;
}

.forgot-password-box {
  width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.forgot-password-header {
  text-align: center;
  margin-bottom: 30px;
}

.icon-wrapper {
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  
  .icon {
    font-size: 40px;
    color: #fff;
  }
}

.forgot-password-header h2 {
  font-size: 24px;
  color: #333;
  margin-bottom: 8px;
}

.forgot-password-header p {
  color: #999;
  font-size: 14px;
}

.forgot-password-form {
  .submit-btn {
    width: 100%;
  }
}

.code-row {
  display: flex;
  width: 100%;
  gap: 8px;
}

.code-row .el-input {
  flex: 1;
}

.code-btn {
  flex-shrink: 0;
  min-width: 120px;
}

.forgot-password-footer {
  text-align: center;
  margin-top: 20px;
  
  a {
    color: #667eea;
    text-decoration: none;
    font-size: 14px;
    
    &:hover {
      text-decoration: underline;
    }
  }
}
</style>