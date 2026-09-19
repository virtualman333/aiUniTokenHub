import { defineStore } from 'pinia'
import axios from 'axios'
import Cookies from 'js-cookie'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
})

// 处理认证/鉴权失败，跳转登录页
function handleAuthRedirect() {
  if (!window.location.pathname.startsWith('/login')) {
    Cookies.remove('token')
    Cookies.remove('userRole')
    ElMessage.warning('登录信息已过期，正在重定向至登录页')
    setTimeout(() => {
      window.location.href = '/login'
    }, 1500)
  }
}

// 响应拦截器 - 处理统一响应格式 {code, msg, data}
api.interceptors.response.use(
  response => {
    const res = response.data
    // 如果是统一响应格式
    if (res && 'code' in res && 'data' in res) {
      // 成功且有业务数据，直接返回 data
      if (res.code >= 200 && res.code < 300) {
        return res.data
      }
      // 认证/鉴权失败场景，跳转登录页
      if (res.code === 401 || res.code === 403) {
        handleAuthRedirect()
      }
      // 错误情况，抛出带有消息的错误
      const error = new Error(res.msg || '操作失败')
      error.response = response
      error.code = res.code
      return Promise.reject(error)
    }
    // 非统一格式，直接返回原数据
    return response.data
  },
  error => {
    // 处理 401/403 认证鉴权失败（HTTP 状态码）
    if (error.response?.status === 401 || error.response?.status === 403) {
      handleAuthRedirect()
    }
    
    // 尝试从后端响应中提取错误信息
    if (error.response?.data) {
      const data = error.response.data
      const msg = data.msg || data.detail || (typeof data === 'string' ? data : '')
      if (msg) {
        error.message = msg
      }
    }
    
    return Promise.reject(error)
  }
)

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = Cookies.get('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null,
    token: Cookies.get('token'),
  }),
  
  getters: {
    isLoggedIn: state => !!state.token,
    isAdmin: state => state.user?.role === 'admin',
  },
  
  actions: {
    async login(username, password) {
      const res = await api.post('/users/auth/login/', { username, password })
      Cookies.set('token', res.token, { expires: 7 })
      Cookies.set('userRole', res.user.role)
      this.user = res.user
      this.token = res.token
      window.location.href = '/app'
      return res
    },
    
    async register(data) {
      const res = await api.post('/users/auth/register/', data)
      Cookies.set('token', res.token, { expires: 7 })
      Cookies.set('userRole', res.user.role)
      this.user = res.user
      this.token = res.token
      return res
    },
    
    async getUserInfo() {
      try {
        const res = await api.get('/users/auth/me/')
        this.user = res
        Cookies.set('userRole', res.role)
        return res
      } catch (e) {
        this.logout()
        throw e
      }
    },
    
    logout() {
      Cookies.remove('token')
      Cookies.remove('userRole')
      this.user = null
      this.token = null
    },
    
    async changePassword(oldPassword, newPassword) {
      return await api.post('/users/auth/change_password/', {
        old_password: oldPassword,
        new_password: newPassword
      })
    },
    
    async sendResetCode(email) {
      // 后端只有一个发码端点 `send_email_code`，按 `purpose` 分流（注册 / 重置密码）。
      // 这里此前打的是 `/users/auth/send_reset_code/` —— 那个路径从来没有存在过，
      // 于是「忘记密码」第一步必然 404，而 ForgotPassword.vue 还把它当成功流程在走。
      return await api.post('/users/auth/send_email_code/', { email, purpose: 'reset_password' })
    },
    
    async resetPassword(email, code, password) {
      return await api.post('/users/auth/reset_password/', {
        email,
        // 字段名跟后端 serializer 走（与 register 同一套：email_code）。
        // 原来这里写的是 `code` —— 就算端点补上了，也会被 serializer 判成缺字段而 400。
        email_code: code,
        password
      })
    },
    
    async fetchApiKeys() {
      return await api.get('/users/keys/')
    },
  }
})

export default api
