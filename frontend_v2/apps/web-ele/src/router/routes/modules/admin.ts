// 管理端路由模块
// 所有管理端页面作为 BasicLayout 的子路由
import type { RouteRecordRaw } from 'vue-router'

import { BasicLayout } from '#/layouts'
import { $t } from '#/locales'

const routes: RouteRecordRaw[] = [
  {
    component: BasicLayout,
    meta: {
      icon: 'lucide:shield',
      order: 100,
      title: $t('page.admin.title'),
    },
    name: 'Admin',
    path: '/admin',
    children: [
      // ─── 控制台（独立，不分组）───
      {
        name: 'AdminDashboard',
        path: '/admin',
        component: () => import('#/views/admin/Dashboard.vue'),
        meta: {
          icon: 'lucide:layout-dashboard',
          title: $t('page.admin.dashboard'),
          affixTab: true,
        },
      },

      // ═══════════════ 用户运营 ═══════════════
      // 分组标题通过 meta.icon 区分，Vben 会自动按 children 排列

      {
        name: 'UserManagement',
        path: '/admin/users',
        component: () => import('#/views/admin/UserManagement.vue'),
        meta: {
          icon: 'lucide:users',
          title: $t('page.admin.userManagement'),
        },
      },
      {
        name: 'CardManagement',
        path: '/admin/card-management',
        component: () => import('#/views/admin/CardManagement.vue'),
        meta: {
          icon: 'lucide:credit-card',
          title: $t('page.admin.cardManagement'),
        },
      },
      {
        name: 'RechargeManagement',
        path: '/admin/recharge-management',
        component: () => import('#/views/admin/RechargeManagement.vue'),
        meta: {
          icon: 'lucide:wallet',
          title: $t('page.admin.rechargeManagement'),
        },
      },
      {
        name: 'BillingManagement',
        path: '/admin/billing-management',
        component: () => import('#/views/admin/BillingManagement.vue'),
        meta: {
          icon: 'lucide:receipt',
          title: $t('page.admin.billingManagement'),
        },
      },
      {
        name: 'InviteManagement',
        path: '/admin/invite-management',
        component: () => import('#/views/admin/InviteManagement.vue'),
        meta: {
          icon: 'lucide:user-plus',
          title: $t('page.admin.inviteManagement'),
        },
      },

      // ═══════════════ API 管理 ═══════════════

      {
        name: 'ModelManagement',
        path: '/admin/model-management',
        component: () => import('#/views/admin/ModelManagement.vue'),
        meta: {
          icon: 'lucide:box',
          title: $t('page.admin.modelManagement'),
        },
      },
      {
        name: 'ProviderManagement',
        path: '/admin/provider-management',
        component: () => import('#/views/admin/ProviderManagement.vue'),
        meta: {
          icon: 'lucide:link',
          title: $t('page.admin.providerManagement'),
        },
      },
      {
        name: 'ChannelManagement',
        path: '/admin/channel-management',
        component: () => import('#/views/admin/ChannelManagement.vue'),
        meta: {
          icon: 'lucide:route',
          title: $t('page.admin.channelManagement'),
        },
      },

      // ═══════════════ 数据监控 ═══════════════

      {
        name: 'AccessLogs',
        path: '/admin/access-logs',
        component: () => import('#/views/admin/AccessLogs.vue'),
        meta: {
          icon: 'lucide:list',
          title: $t('page.admin.accessLogs'),
        },
      },
      {
        name: 'RedisManagement',
        path: '/admin/redis-management',
        component: () => import('#/views/admin/RedisManagement.vue'),
        meta: {
          icon: 'lucide:database',
          title: $t('page.admin.redisManagement'),
        },
      },

      // ═══════════════ 工单与客服 ═══════════════

      {
        name: 'TicketManagement',
        path: '/admin/ticket-management',
        component: () => import('#/views/admin/TicketManagement.vue'),
        meta: {
          icon: 'lucide:ticket',
          title: $t('page.admin.ticketManagement'),
        },
      },

      // ═══════════════ 系统设置 ═══════════════

      {
        name: 'SystemSettings',
        path: '/admin/system-settings',
        component: () => import('#/views/admin/SystemSettings.vue'),
        meta: {
          icon: 'lucide:settings',
          title: $t('page.admin.systemSettings'),
        },
      },

      // ─── 隐藏页面（hideInMenu） ───
      {
        name: 'AdminSettings',
        path: '/admin/settings',
        component: () => import('#/views/admin/Settings.vue'),
        meta: {
          hideInMenu: true,
          icon: 'lucide:wrench',
          title: $t('page.admin.settings'),
        },
      },
    ],
  },
]

export default routes
