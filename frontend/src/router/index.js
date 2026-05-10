import { createRouter, createWebHistory } from 'vue-router'
import Cookies from 'js-cookie'

const routes = [
  // 公共路由 - 首页（未登录可访问）
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: {
      title: 'uniTokenHub - 统一API中转服务',
      description: 'uniTokenHub 是开箱即用的API中转站框架，支持AI API聚合、OpenAI兼容接口、多模型管理。快速搭建自己的API聚合平台。',
      keywords: 'API中转,API网关,AI API,OpenAI API,API聚合,大模型接入',
      guest: true
    }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: {
      title: '登录',
      description: '登录 uniTokenHub，管理您的API密钥和使用情况。支持API中转服务、AI模型调用、计费管理。',
      keywords: 'uniTokenHub登录,API管理平台登录',
      guest: true
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: {
      title: '注册',
      description: '注册 uniTokenHub 账户，获取API中转服务。支持多种AI模型接入，提供稳定可靠的API网关服务。',
      keywords: 'uniTokenHub注册,API中转服务注册',
      guest: true
    }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/ForgotPassword.vue'),
    meta: {
      title: '忘记密码',
      description: '重置 uniTokenHub 账户密码，找回您的API管理平台访问权限。',
      keywords: 'uniTokenHub,忘记密码,重置密码',
      guest: true
    }
  },
  {
    path: '/privacy-policy',
    name: 'PrivacyPolicy',
    component: () => import('@/views/PrivacyPolicy.vue'),
    meta: {
      title: '隐私政策',
      description: 'uniTokenHub 隐私政策 - 了解我们如何收集、使用和保护您的个人信息。',
      keywords: 'uniTokenHub,隐私政策,数据保护',
      guest: true
    }
  },
  {
    path: '/terms-of-service',
    name: 'TermsOfService',
    component: () => import('@/views/TermsOfService.vue'),
    meta: {
      title: '用户协议',
      description: 'uniTokenHub 用户服务协议 - 了解使用条款和条件。',
      keywords: 'uniTokenHub,用户协议,服务条款',
      guest: true
    }
  },
  
  // 用户端布局
  {
    path: '/app',
    component: () => import('@/layouts/UserLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/user/Dashboard/index.vue'),
        meta: {
          title: '控制台',
          description: 'uniTokenHub 用户控制台 - 查看API使用统计、消费明细和数据看板。',
          keywords: 'API控制台,使用统计,消费明细'
        }
      },
      {
        path: 'api-doc',
        name: 'APIDoc',
        component: () => import('@/views/user/APIDoc.vue'),
        meta: {
          title: '接口文档',
          description: 'uniTokenHub API 接口文档 - 在线文档、请求示例和接入指南。',
          keywords: 'API文档,接口文档,API接入指南'
        }
      },
      {
        path: 'model-square',
        name: 'ModelSquare',
        component: () => import('@/views/user/ModelSquare/index.vue'),
        meta: {
          title: '模型广场',
          description: 'uniTokenHub 模型广场 - 浏览支持的AI模型，了解各模型的价格和使用说明。',
          keywords: 'AI模型,大模型,GPT-4,Claude,Gemini'
        }
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/user/Chat/index.vue'),
        meta: {
          title: 'AI 对话',
          description: 'uniTokenHub AI 对话 - 在线测试AI模型，体验GPT、Claude等大模型能力。',
          keywords: 'AI对话,在线聊天,GPT测试,AI测试'
        }
      },
      {
        path: 'my-keys',
        name: 'MyKeys',
        component: () => import('@/views/user/MyKeys/index.vue'),
        meta: {
          title: '我的密钥',
          description: 'uniTokenHub 密钥管理 - 创建和管理您的API密钥，安全访问API服务。',
          keywords: 'API密钥,密钥管理,API Key'
        }
      },
      {
        path: 'usage-log',
        name: 'UsageLog',
        component: () => import('@/views/user/UsageLog/index.vue'),
        meta: {
          title: '使用记录',
          description: 'uniTokenHub 使用记录 - 查看API请求日志、消费详情和使用统计。',
          keywords: 'API日志,使用记录,请求统计'
        }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/user/Settings/index.vue'),
        meta: {
          title: '账户设置',
          description: 'uniTokenHub 账户设置 - 管理个人信息、修改密码和账户配置。',
          keywords: '账户设置,个人信息,密码修改'
        }
      },
      {
        path: 'billing',
        name: 'Billing',
        component: () => import('@/views/user/Billing/index.vue'),
        meta: {
          title: '账单中心',
          description: 'uniTokenHub 账单中心 - 管理账户余额、查看充值记录和消费账单。',
          keywords: '账单中心,账户充值,消费记录'
        }
      },
      {
        path: 'tickets',
        name: 'Tickets',
        component: () => import('@/views/user/Tickets/index.vue'),
        meta: {
          title: '工单中心',
          description: 'uniTokenHub 工单中心 - 提交问题反馈，查看工单处理进度。',
          keywords: '工单中心,问题反馈,技术支持'
        }
      },
      {
        path: 'tutorial',
        name: 'Tutorial',
        component: () => import('@/views/user/Tutorial/index.vue'),
        meta: {
          title: '接入教程',
          description: 'uniTokenHub 接入教程 - 学习如何快速接入和使用API中转服务。',
          keywords: '接入教程,API教程,快速上手'
        }
      },
    ]
  },
  
  // 管理端布局（noIndex: true 因为管理页面不需要被搜索引擎索引）
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, noIndex: true },
    children: [
      {
        path: '',
        name: 'AdminDashboard',
        component: () => import('@/views/admin/Dashboard.vue'),
        meta: { title: '管理后台', noIndex: true }
      },
      {
        path: 'users',
        name: 'UserManagement',
        component: () => import('@/views/admin/UserManagement.vue'),
        meta: { title: '用户管理', noIndex: true }
      },
      {
        path: 'access-logs',
        name: 'AccessLogs',
        component: () => import('@/views/admin/AccessLogs.vue'),
        meta: { title: '接口使用记录', noIndex: true }
      },
      {
        path: 'model-management',
        name: 'ModelManagement',
        component: () => import('@/views/admin/ModelManagement.vue'),
        meta: { title: '模型管理', noIndex: true }
      },
      {
        path: 'provider-management',
        name: 'ProviderManagement',
        component: () => import('@/views/admin/ProviderManagement.vue'),
        meta: { title: '供应商管理', noIndex: true }
      },
      {
        path: 'channel-management',
        name: 'ChannelManagement',
        component: () => import('@/views/admin/ChannelManagement.vue'),
        meta: { title: '渠道管理', noIndex: true }
      },
      {
        path: 'settings',
        name: 'AdminSettings',
        component: () => import('@/views/admin/Settings.vue'),
        meta: { title: '个人设置', noIndex: true }
      },
      {
        path: 'system-settings',
        name: 'SystemSettings',
        component: () => import('@/views/admin/SystemSettings.vue'),
        meta: { title: '系统设置', noIndex: true }
      },
      {
        path: 'ticket-management',
        name: 'TicketManagement',
        component: () => import('@/views/admin/TicketManagement.vue'),
        meta: { title: '工单管理', noIndex: true }
      },
      {
        path: 'card-management',
        name: 'CardManagement',
        component: () => import('@/views/admin/CardManagement.vue'),
        meta: { title: '卡密管理', noIndex: true }
      },
      {
        path: 'invite-management',
        name: 'InviteManagement',
        component: () => import('@/views/admin/InviteManagement.vue'),
        meta: { title: '邀请返利', noIndex: true }
      },
      {
        path: 'billing-management',
        name: 'BillingManagement',
        component: () => import('@/views/admin/BillingManagement.vue'),
        meta: { title: '账单管理', noIndex: true }
      },
      {
        path: 'recharge-management',
        name: 'RechargeManagement',
        component: () => import('@/views/admin/RechargeManagement.vue'),
        meta: { title: '充值管理', noIndex: true }
      },
      {
        path: 'traffic-analysis',
        name: 'TrafficAnalysis',
        component: () => import('@/views/admin/TrafficAnalysis.vue'),
        meta: { title: '流量分析', noIndex: true }
      },
      {
        path: 'redis-management',
        name: 'RedisManagement',
        component: () => import('@/views/admin/RedisManagement.vue'),
        meta: { title: 'Redis管理', noIndex: true }
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
  const token = Cookies.get('token')
  const userRole = Cookies.get('userRole')

  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.meta.guest && token) {
    // 已登录用户访问 guest 路由，都跳转到用户端
    next('/app')
  } else if (to.meta.requiresAdmin && userRole !== 'admin') {
    // 非管理员访问管理员路由，跳转到用户端
    next('/app')
  } else {
    next()
  }
})

// 路由后置守卫 - 动态更新 Meta 标签（SEO 优化）
router.afterEach((to) => {
  // 从 route meta 中获取 SEO 信息
  const title = to.meta.title || 'uniTokenHub'
  const description = to.meta.description || 'uniTokenHub - 开箱即用的统一API中转服务与网关框架，支持AI API聚合、OpenAI兼容接口、多模型管理。'
  const keywords = to.meta.keywords || 'API中转,API网关,AI API,OpenAI API'
  const noIndex = to.meta.noIndex || false

  // 更新 title
  document.title = to.meta.title ? `${to.meta.title} | uniTokenHub` : 'uniTokenHub'

  // 动态更新 meta 标签
  updateMetaTag('name', 'description', description)
  updateMetaTag('name', 'keywords', keywords)
  updateMetaTag('name', 'robots', noIndex ? 'noindex, nofollow' : 'index, follow, max-image-preview:large, max-snippet:-1')

  // 更新 Open Graph 标签
  updateMetaTag('property', 'og:title', title)
  updateMetaTag('property', 'og:description', description)
  updateMetaTag('property', 'og:url', window.location.href)

  // 更新 Twitter Card 标签
  updateMetaTag('name', 'twitter:title', title)
  updateMetaTag('name', 'twitter:description', description)

  // 更新 canonical 链接
  updateCanonicalLink(window.location.href)
})

/**
 * 更新 meta 标签的辅助函数
 * @param {string} attr - 属性名 ('name' 或 'property')
 * @param {string} key - meta 标签的键
 * @param {string} content - meta 标签的内容
 */
function updateMetaTag(attr, key, content) {
  let meta = document.querySelector(`meta[${attr}="${key}"]`)
  if (!meta) {
    meta = document.createElement('meta')
    meta.setAttribute(attr, key)
    document.head.appendChild(meta)
  }
  meta.setAttribute('content', content)
}

/**
 * 更新 canonical 链接
 * @param {string} url - 规范的 URL
 */
function updateCanonicalLink(url) {
  let link = document.querySelector('link[rel="canonical"]')
  if (!link) {
    link = document.createElement('link')
    link.setAttribute('rel', 'canonical')
    document.head.appendChild(link)
  }
  link.setAttribute('href', url)
}

export default router
