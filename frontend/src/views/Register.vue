<template>
  <div class="register-container">
    <div class="register-box">
      <div class="register-header">
        <img :src="logoSrc" alt="logo" class="logo-img" />
        <h2>创建账号</h2>
        <p>加入 uniTokenHub</p>
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
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Message, Lock, Link, Key } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores'
import api from '@/stores'
import logoSrc from '@/assets/image/logo.jpeg'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

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
.register-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
