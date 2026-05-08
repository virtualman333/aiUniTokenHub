<template>
  <div class="register-page">
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
    
    <div class="register-container">
      <div class="register-box">
        <div class="register-header">
          <img :src="logoSrc" alt="logo" class="logo-img" />
          <h2>{{ t('auth.createAccount') }}</h2>
          <p>{{ t('auth.joinUs') }}</p>
        </div>
      
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="register-form"
        @submit.prevent="handleRegister"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            placeholder="邮箱"
            size="large"
            :prefix-icon="Message"
          />
        </el-form-item>

        <el-form-item prop="email_code">
          <div class="code-row">
            <el-input
              v-model="form.email_code"
              placeholder="邮箱验证码（6位）"
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
        
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码（至少6位）"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        
        <el-form-item prop="password_confirm">
          <el-input
            v-model="form.password_confirm"
            type="password"
            placeholder="确认密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleRegister"
          />
        </el-form-item>
        
        <el-form-item prop="invite_code">
          <el-input
            v-model="form.invite_code"
            placeholder="邀请码（选填）"
            size="large"
            :prefix-icon="Link"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="register-btn"
            @click="handleRegister"
          >
            注 册
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="register-footer">
        <span>已有账号？</span>
        <router-link to="/login">立即登录</router-link>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Message, Lock, Link, Key } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores'
import api from '@/stores'
import logoSrc from '@/assets/image/logo.png'
import { useI18n } from '@/composables/useI18n'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const { t } = useI18n()

const formRef = ref()
const loading = ref(false)
const sendingCode = ref(false)
const countdown = ref(0)
let timer = null

const form = reactive({
  username: '',
  email: '',
  email_code: '',
  password: '',
  password_confirm: '',
  invite_code: ''
})

onMounted(() => {
  const inviteCode = route.query.invite
  if (inviteCode) {
    form.invite_code = inviteCode
  }
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})

const validatePasswordConfirm = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  email_code: [
    { required: true, message: '请输入邮箱验证码', trigger: 'blur' },
    { len: 6, message: '验证码为 6 位数字', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少为6位', trigger: 'blur' }
  ],
  password_confirm: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validatePasswordConfirm, trigger: 'blur' }
  ]
}

const codeBtnDisabled = computed(() => sendingCode.value || countdown.value > 0)
const codeBtnText = computed(() => {
  if (countdown.value > 0) return `${countdown.value}s 后重试`
  return '获取验证码'
})

function startCountdown(seconds) {
  countdown.value = seconds
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      clearInterval(timer)
      timer = null
    }
  }, 1000)
}

async function handleSendCode() {
  // 单独校验邮箱
  try {
    await formRef.value.validateField('email')
  } catch {
    return
  }
  if (!form.email) {
    ElMessage.warning('请先输入邮箱')
    return
  }
  sendingCode.value = true
  try {
    const res = await api.post('/users/auth/send_email_code/', {
      email: form.email,
      purpose: 'register'
    })
    ElMessage.success('验证码已发送，请查收邮件')
    const wait = Number(res?.resend_seconds) || 60
    startCountdown(wait)
  } catch (error) {
    ElMessage.error(error?.message || '发送失败')
  } finally {
    sendingCode.value = false
  }
}

const handleRegister = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.register(form)
    ElMessage.success('注册成功')
    router.push('/')
  } catch (error) {
    ElMessage.error(error.message || '注册失败')
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

.register-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  padding-top: 100px;
}

.register-box {
  width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.register-header {
  text-align: center;
  margin-bottom: 30px;
  
  .logo-img {
    width: 64px;
    height: 64px;
    border-radius: 16px;
    object-fit: cover;
    margin-bottom: 12px;
    box-shadow: 0 6px 18px rgba(102, 126, 234, 0.25);
  }
  
  h2 {
    font-size: 24px;
    color: #333;
    margin-bottom: 8px;
  }
  
  p {
    color: #999;
    font-size: 14px;
  }
}

.register-form {
  .register-btn {
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

.register-footer {
  text-align: center;
  margin-top: 20px;
  color: #666;
  
  a {
    color: #667eea;
    text-decoration: none;
    margin-left: 5px;
    
    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
