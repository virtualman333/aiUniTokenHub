/**
 * 管理后台菜单配置（二级：顶部分类 + 左侧子菜单）
 *
 * 结构说明：
 * - groups: 顶部一级分类导航
 *   - key: 分类标识
 *   - title: 显示名称
 *   - icon: 图标
 *   - defaultPath: 默认选中的子菜单路径
 *   - children: 该分类下的左侧子菜单
 * - affix: true 表示标签页固定不可关闭
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
  Tools
} from '@element-plus/icons-vue'

/** 独立页面（不归属任何分组） */
export const standalonePages = [
  {
    path: '/admin',
    title: '控制台',
    icon: markRaw(HomeFilled),
    affix: true
  }
]

/** 分组配置（用于顶部导航） */
export const menuGroups = [
  // ═══════════════ 用户运营 ═══════════════
  {
    key: 'user',
    title: '用户运营',
    icon: markRaw(User),
    defaultPath: '/admin/users',
    children: [
      { path: '/admin/users',              title: '用户管理',     icon: markRaw(User)       },
      { path: '/admin/card-management',     title: '卡密管理',     icon: markRaw(CreditCard)  },
      { path: '/admin/recharge-management', title: '充值管理',     icon: markRaw(Wallet)      },
      { path: '/admin/billing-management',  title: '账单管理',     icon: markRaw(Wallet)      },
      { path: '/admin/invite-management',   title: '邀请返利',     icon: markRaw(Share)       },
    ]
  },

  // ═══════════════ API 管理 ═══════════════
  {
    key: 'api',
    title: 'API 管理',
    icon: markRaw(Connection),
    defaultPath: '/admin/model-management',
    children: [
      { path: '/admin/model-management',    title: '模型管理',     icon: markRaw(Box)         },
      { path: '/admin/provider-management',  title: '供应商管理',   icon: markRaw(Connection)  },
      { path: '/admin/channel-management',   title: '渠道管理',     icon: markRaw(Guide)        },
    ]
  },

  // ═══════════════ 数据监控 ═══════════════
  {
    key: 'monitor',
    title: '数据监控',
    icon: markRaw(DataAnalysis),
    defaultPath: '/admin/access-logs',
    children: [
      { path: '/admin/access-logs',     title: '接口使用记录', icon: markRaw(List)  },
      { path: '/admin/redis-management', title: 'Redis管理',   icon: markRaw(Coin)  },
    ]
  },

  // ═══════════════ 工单系统 ═══════════════
  {
    key: 'ticket',
    title: '工单与客服',
    icon: markRaw(Tickets),
    defaultPath: '/admin/ticket-management',
    children: [
      { path: '/admin/ticket-management', title: '工单管理', icon: markRaw(Tickets) },
    ]
  },

  // ═══════════════ 系统 ═══════════════
  {
    key: 'system',
    title: '系统设置',
    icon: markRaw(Setting),
    defaultPath: '/admin/system-settings',
    children: [
      { path: '/admin/system-settings', title: '系统设置', icon: markRaw(Setting) },
    ]
  },
]

/** 隐藏页面（不出现在菜单中，但可被标签页识别） */
export const hiddenPages = [
  { path: '/admin/settings', title: '个人设置', icon: markRaw(Tools), hidden: true },
]

// ─────────────────────────────────────────────
// 兼容旧接口 & 工具函数
// ─────────────────────────────────────────────

/** 扁平化的所有可导航菜单项 */
export function getFlatMenuItems() {
  return [
    ...standalonePages,
    ...menuGroups.flatMap(g => g.children),
    ...hiddenPages.filter(p => p.path)
  ]
}

/** 根据 path 查找菜单项 */
export function findMenuItem(path) {
  return getFlatMenuItems().find(item => item.path === path)
}

/** 根据 path 找到所属分组 */
export function findGroupByPath(path) {
  for (const g of menuGroups) {
    if (g.children.some(c => c.path === path)) return g
  }
  return null
}

/** 获取所有需要 affix 的路径 */
export function getAffixTags() {
  return getFlatMenuItems()
    .filter(item => item.affix)
    .map(item => ({
      path: item.path,
      title: item.title,
      name: item.name,
      affix: true
    }))
}

/** 兼容旧导出名 */
export const adminMenu = getFlatMenuItems()
