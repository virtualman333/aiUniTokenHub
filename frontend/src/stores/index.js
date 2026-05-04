import { defineStore } from 'pinia'
import axios from 'axios'
import Cookies from 'js-cookie'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

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

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      Cookies.remove('token')
      Cookies.remove('userRole')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
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

export const useAPIStore = defineStore('api', {
  state: () => ({
    categories: [],
    endpoints: [],
  }),
  
  actions: {
    async fetchCategories() {
      this.categories = await api.get('/proxy/categories/')
      return this.categories
    },
    
    async fetchEndpoints(categoryId) {
      const params = categoryId ? { category: categoryId } : {}
      this.endpoints = await api.get('/proxy/endpoints/', { params })
      return this.endpoints
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
      this.requestStats = await api.get('/dashboard/request_stats/', { params: { days } })
      return this.requestStats
    },
    
    async fetchTopAPIs(limit = 10) {
      this.topAPIs = await api.get('/dashboard/top_apis/', { params: { limit } })
      return this.topAPIs
    },
  }
})

export default api
