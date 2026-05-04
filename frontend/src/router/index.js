import { createRouter, createWebHistory } from 'vue-router'
import Cookies from 'js-cookie'

const routes = [
  // 公共路由
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { title: '注册', guest: true }
  },
  
  // 用户端布局
  {
    path: '/',
    component: () => import('@/layouts/UserLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/user/Dashboard.vue'),
        meta: { title: '控制台' }
      },
      {
        path: 'api-list',
        name: 'APIList',
        component: () => import('@/views/user/APIList.vue'),
        meta: { title: 'API列表' }
      },
      {
        path: 'model-square',
        name: 'ModelSquare',
        component: () => import('@/views/user/ModelSquare/index.vue'),
        meta: { title: '模型广场' }
      },
      {
        path: 'api-doc/:id',
        name: 'APIDoc',
        component: () => import('@/views/user/APIDoc.vue'),
        meta: { title: 'API文档' }
      },
      {
        path: 'my-keys',
        name: 'MyKeys',
        component: () => import('@/views/user/MyKeys.vue'),
        meta: { title: '我的密钥' }
      },
      {
        path: 'usage-log',
        name: 'UsageLog',
        component: () => import('@/views/user/UsageLog.vue'),
        meta: { title: '使用记录' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/user/Settings.vue'),
        meta: { title: '账户设置' }
      },
      {
        path: 'billing',
        name: 'Billing',
        component: () => import('@/views/user/Billing.vue'),
        meta: { title: '账单中心' }
      },
    ]
  },
  
  // 管理端布局
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      {
        path: '',
        name: 'AdminDashboard',
        component: () => import('@/views/admin/Dashboard.vue'),
        meta: { title: '管理后台' }
      },
      {
        path: 'users',
        name: 'UserManagement',
        component: () => import('@/views/admin/UserManagement.vue'),
        meta: { title: '用户管理' }
      },
      {
        path: 'api-management',
        name: 'APIManagement',
        component: () => import('@/views/admin/APIManagement.vue'),
        meta: { title: 'API管理' }
      },
      {
        path: 'api-categories',
        name: 'APICategories',
        component: () => import('@/views/admin/APICategories.vue'),
        meta: { title: 'API分类' }
      },
      {
        path: 'access-logs',
        name: 'AccessLogs',
        component: () => import('@/views/admin/AccessLogs.vue'),
        meta: { title: '访问日志' }
      },
      {
        path: 'model-management',
        name: 'ModelManagement',
        component: () => import('@/views/admin/ModelManagement.vue'),
        meta: { title: '模型管理' }
      },
      {
        path: 'channel-management',
        name: 'ChannelManagement',
        component: () => import('@/views/admin/ChannelManagement.vue'),
        meta: { title: '渠道管理' }
      },
    ]
  },
  
  // 404
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - uniTokenHub` : 'uniTokenHub'
  
  const token = Cookies.get('token')
  const userRole = Cookies.get('userRole')
  
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.meta.guest && token) {
    next('/')
  } else if (to.meta.requiresAdmin && userRole !== 'admin') {
    next('/')
  } else {
    next()
  }
})

export default router
