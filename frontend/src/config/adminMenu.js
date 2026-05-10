/**
 * 管理后台菜单配置（分组 + 二级菜单）
 * 
 * 结构说明：
 * - type: 'group' 表示分组标题（不可点击），'item' 表示可导航菜单项
 * - affix: true 表示标签页固定不可关闭
 * - hidden: true 表示不在侧边栏显示（但仍可通过路由访问）
 */
import { markRaw } from 'vue'
import {
  HomeFilled,
  User,
  CreditCard,
  Wallet,
  Share,
  List,
  Coin,
  Box,
  Connection,
  Guide,
  Tickets,
  Setting,
  Monitor,
  DataAnalysis,
  OfficeBuilding,
  Tools
} from '@element-plus/icons-vue'

export const adminMenu = [
  // ─── 控制台（独立，不分组） ───
  {
    path: '/admin',
    title: '控制台',
    icon: markRaw(HomeFilled),
    affix: true
  },

  // ═══════════════ 用户运营 ═══════════════
  {
    type: 'group',
    title: '用户运营',
    icon: markRaw(User)
  },
  { path: '/admin/users',           title: '用户管理',     icon: markRaw(User),       group: 'user' },
  { path: '/admin/card-management',  title: '卡密管理',     icon: markRaw(CreditCard),  group: 'user' },
  { path: '/admin/recharge-management', title: '充值管理',   icon: markRaw(Wallet),      group: 'user' },
  { path: '/admin/billing-management',  title: '账单管理',   icon: markRaw(Wallet),      group: 'user' },
  { path: '/admin/invite-management',   title: '邀请返利',   icon: markRaw(Share),       group: 'user' },

  // ═══════════════ API 管理 ═══════════════
  {
    type: 'group',
    title: 'API 管理',
    icon: markRaw(Connection)
  },
  { path: '/admin/model-management',     title: '模型管理',     icon: markRaw(Box),         group: 'api' },
  { path: '/admin/provider-management',   title: '供应商管理',   icon: markRaw(Connection),  group: 'api' },
  { path: '/admin/channel-management',    title: '渠道管理',     icon: markRaw(Guide),        group: 'api' },

  // ═══════════════ 数据监控 ═══════════════
  {
    type: 'group',
    title: '数据监控',
    icon: markRaw(DataAnalysis)
  },
  { path: '/admin/access-logs',     title: '接口使用记录', icon: markRaw(List),  group: 'monitor' },
  { path: '/admin/redis-management', title: 'Redis管理',    icon: markRaw(Coin),  group: 'monitor' },

  // ═══════════════ 工单系统 ═══════════════
  {
    type: 'group',
    title: '工单与客服',
    icon: markRaw(Tickets)
  },
  { path: '/admin/ticket-management', title: '工单管理', icon: markRaw(Tickets), group: 'ticket' },

  // ═══════════════ 系统 ═══════════════
  {
    type: 'group',
    title: '系统设置',
    icon: markRaw(Setting)
  },
  { path: '/admin/system-settings', title: '系统设置', icon: markRaw(Setting), group: 'system' },

  // ─── 隐藏页面（不出现在侧边栏，但可被标签页识别） ───
  { path: '/admin/settings', title: '个人设置', icon: markRaw(Tools), hidden: true },
]

/** 获取扁平化的可导航菜单列表（用于标签页匹配等） */
export function getFlatMenuItems() {
  return adminMenu.filter(item => item.path && !item.type)
}

/** 根据 path 菜单项 */
export function findMenuItem(path) {
  return adminMenu.find(item => item.path === path)
}

/** 获取所有需要 affix 的路径 */
export function getAffixTags() {
  return getFlatMenuItems().filter(item => item.affix).map(item => ({
    path: item.path,
    title: item.title,
    name: item.name,
    affix: true
  }))
}
