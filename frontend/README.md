# uniTokenHub Frontend

## 技术栈
- Vue 3 + Composition API
- Vite
- Vue Router 4
- Pinia
- Element Plus
- Axios
- ECharts

## 安装

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build

# 预览
npm run preview
```

## 项目结构

```
src/
├── api/              # API相关
├── assets/           # 静态资源
├── components/       # 公共组件
├── layouts/          # 布局组件
│   ├── AdminLayout.vue    # 管理端布局
│   └── UserLayout.vue     # 用户端布局
├── router/           # 路由配置
├── stores/           # 状态管理
├── styles/           # 全局样式
├── utils/            # 工具函数
└── views/            # 页面视图
    ├── admin/        # 管理端页面
    └── user/         # 用户端页面
```

## 功能模块

### 用户端
- 控制台：数据总览、请求趋势
- API列表：分类浏览、API搜索
- API文档：请求示例、在线测试
- 我的密钥：密钥管理
- 使用记录：调用日志
- 账户设置：个人信息、密码修改

### 管理端
- 总览：全局数据统计
- 用户管理：用户列表、状态管理
- API管理：增删改查
- API分类：分类管理
- 访问日志：全量日志查询
