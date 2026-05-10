import type { RouteRecordStringComponent } from '@vben/types';

/**
 * 静态菜单配置 - 后端无菜单 API，直接返回静态路由
 * 根据用户角色动态过滤菜单项
 */

const staticMenus: RouteRecordStringComponent[] = [
  {
    component: 'basic/outer',
    meta: {
      icon: 'lucide:home',
      order: -1,
      title: '首页',
    },
    name: 'Home',
    path: '/',
  },
  {
    component: 'basic',
    meta: {
      icon: 'lucide:layout-dashboard',
      title: '控制台',
    },
    name: 'Dashboard',
    path: '/dashboard',
    children: [
      {
        name: 'DashboardOverview',
        path: '/dashboard/overview',
        component: '/views/dashboard/index',
        meta: { icon: 'lucide:bar-chart-3', title: '概览' },
      },
    ],
  },
  {
    component: 'basic',
    meta: {
      icon: 'lucide:key-round',
      title: 'API 密钥',
    },
    name: 'ApiKey',
    path: '/api-key',
    children: [
      {
        name: 'ApiKeyList',
        path: '/api-key/list',
        component: '/views/api-key/index',
        meta: { icon: 'lucide:list', title: '密钥管理' },
      },
    ],
  },
  {
    component: 'basic',
    meta: {
      icon: 'lucide:bot',
      title: 'AI 模型',
    },
    name: 'Models',
    path: '/models',
    children: [
      {
        name: 'ModelList',
        path: '/models/list',
        component: '/views/models/index',
        meta: { icon: 'lucide:cubes', title: '模型列表' },
      },
      {
        name: 'ModelProviders',
        path: '/models/providers',
        component: '/views/models/providers',
        meta: { icon: 'lucide:server', title: '模型提供商' },
      },
    ],
  },
  {
    component: 'basic',
    meta: {
      icon: 'lucide:wallet',
      title: '账单中心',
    },
    name: 'Billing',
    path: '/billing',
    children: [
      {
        name: 'BillList',
        path: '/billing/bills',
        component: '/views/billing/bills',
        meta: { icon: 'lucide:receipt', title: '账单记录' },
      },
      {
        name: 'Recharge',
        path: '/billing/recharge',
        component: '/views/billing/recharge',
        meta: { icon: 'lucide:credit-card', title: '充值' },
      },
    ],
  },
  {
    component: 'basic',
    meta: {
      icon: 'lucide:ticket',
      title: '工单系统',
    },
    name: 'Tickets',
    path: '/tickets',
    children: [
      {
        name: 'TicketList',
        path: '/tickets/list',
        component: '/views/tickets/index',
        meta: { icon: 'lucide:inbox', title: '我的工单' },
      },
      {
        name: 'CreateTicket',
        path: '/tickets/create',
        component: '/views/tickets/create',
        meta: { icon: 'lucide:plus-circle', title: '提交工单' },
      },
    ],
  },
  {
    component: 'basic',
    meta: {
      icon: 'lucide:user-cog',
      title: '个人设置',
    },
    name: 'Settings',
    path: '/settings',
    children: [
      {
        name: 'Profile',
        path: '/settings/profile',
        component: '/views/settings/profile',
        meta: { icon: 'lucide:user', title: '个人信息' },
      },
      {
        name: 'Security',
        path: '/settings/security',
        component: '/views/settings/security',
        meta: { icon: 'lucide:shield', title: '安全设置' },
      },
    ],
  },
];

/** 管理员专属菜单 */
const adminMenus: RouteRecordStringComponent[] = [
  {
    component: 'basic',
    meta: {
      icon: 'lucide:shield-alert',
      title: '系统管理',
    },
    name: 'Admin',
    path: '/admin',
    children: [
      {
        name: 'AdminDashboard',
        path: '/admin/dashboard',
        component: '/views/admin/Dashboard',
        meta: { icon: 'lucide:gauge', title: '管理面板' },
      },
      {
        name: 'AdminUsers',
        path: '/admin/users',
        component: '/views/admin/Users',
        meta: { icon: 'lucide:users', title: '用户管理' },
      },
      {
        name: 'AdminModels',
        path: '/admin/models',
        component: '/views/admin/Models',
        meta: { icon: 'lucide:cpu', title: '模型管理' },
      },
      {
        name: 'AdminCards',
        path: '/admin/cards',
        component: '/views/admin/Cards',
        meta: { icon: 'lucide:credit-card', title: '卡密管理' },
      },
      {
        name: 'AdminRecharge',
        path: '/admin/recharge',
        component: '/views/admin/Recharge',
        meta: { icon: 'lucide:banknote', title: '充值管理' },
      },
      {
        name: 'AdminTickets',
        path: '/admin/tickets',
        component: '/views/admin/Tickets',
        meta: { icon: 'lucide:ticket-check', title: '工单管理' },
      },
      {
        name: 'AdminSystem',
        path: '/admin/system',
        component: '/views/admin/System',
        meta: { icon: 'lucide:settings-2', title: '系统设置' },
      },
    ],
  },
];

/**
 * 获取所有菜单 - 返回静态菜单 + 管理员菜单（如果需要）
 */
export async function getAllMenusApi() {
  // 返回合并后的静态菜单
  return [...staticMenus, ...adminMenus];
}
