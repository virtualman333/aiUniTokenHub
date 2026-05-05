import { defineStore } from 'pinia'
import axios from 'axios'
import Cookies from 'js-cookie'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

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
    if (error.response?.status === 401) {
      Cookies.remove('token')
      Cookies.remove('userRole')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = Cookies.get('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
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
  }
})

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    overview: {},
    requestStats: [],
    topAPIs: [],
  }),
  
  actions: {
    async fetchOverview() {
      this.overview = await api.get('/dashboard/overview/')
      return this.overview
    },
    
    async fetchRequestStats(days = 7) {
      this.requestStats = await api.get('/dashboard/trend/', { params: { days } })
      return this.requestStats
    },
    
    async fetchTopAPIs(limit = 10) {
      this.topAPIs = await api.get('/dashboard/distribution/', { params: { limit } })
      return this.topAPIs
    },
  }
})

export default api
