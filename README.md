# uniTokenHub

开箱即用的 API 中转站框架 / 统一 API 网关服务

## 🚀 项目简介

uniTokenHub 是一个功能完整、开箱即用的 API 中转站/网关服务框架，专为构建自己的 API 聚合平台而设计。无论你是想做 AI API 中转、OpenAI 兼容服务、还是通用 API 网关，这个框架都能帮你快速搭建。

### ✨ 核心功能

- **API 代理转发** - 支持多种上游 API 提供商，统一入口
- **密钥管理** - 用户自主创建 API Key，安全认证
- **计费系统** - 灵活的计费规则，支持预付费
- **使用统计** - 详细的请求记录、消费明细、数据看板
- **用户管理** - 完整的用户注册、登录、权限管理
- **管理员后台** - 全功能管理面板，用户/API/日志一键管理
- **会话管理** - 支持对话历史记录
- **多模型支持** - 可扩展的模型管理系统

## 🛠️ 技术栈

| 组件 | 技术选型 |
|------|---------|
| 后端框架 | Django 4.2 + Django REST Framework |
| 数据库 | MySQL 5.7+ |
| 缓存 | Redis (可选) |
| 管理后台 | Django SimpleUI |
| 认证 | JWT (PyJWT) |
| 前端框架 | Vue 3 + Composition API |
| 构建工具 | Vite 5 |
| UI 框架 | Element Plus |
| 状态管理 | Pinia |
| 路由 | Vue Router 4 |
| HTTP 客户端 | Axios |
| 图表库 | ECharts 5 |
| Markdown | marked + highlight.js |
| 日期处理 | dayjs |

## 📁 项目结构

```
uniTokenHub/
├── backend/              # Django 后端服务
│   ├── apps/
│   │   ├── users/        # 用户认证、账户、密钥管理
│   │   ├── api_proxy/    # API 代理、请求转发、日志记录
│   │   └── ai_models/    # 模型管理、上游账户配置
│   ├── config/           # 配置文件
│   ├── manage.py
│   └── requirements.txt
│
├── frontend/             # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── user/     # 用户端页面
│   │   │   └── admin/    # 管理端页面
│   │   └── stores/
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+

### 1. 后端部署

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，配置数据库、Redis 等

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建管理员
python manage.py createsuperuser

# 初始化测试数据（可选）
python init_test_users.py

# 启动服务
python manage.py runserver
```

### 2. 前端部署

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build

# 构建并打包为 zip
npm run build:zip
```

## 🔧 配置说明

### 环境变量 (.env)

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DEBUG | 调试模式 | True |
| SECRET_KEY | Django 密钥 | dev-secret-key-change-in-production |
| DB_NAME | 数据库名 | unitokenhub |
| DB_USER | 数据库用户名 | unitokenhub |
| DB_PASSWORD | 数据库密码 | unitokenhub |
| DB_HOST | 数据库主机 | 127.0.0.1 |
| DB_PORT | 数据库端口 | 3306 |
| REDIS_URL | Redis 连接 | (可选) |
| ALLOWED_HOSTS | 允许的主机 | * |

### 管理后台

启动服务后访问：
- 管理员后台: `http://localhost:8000/admin/`
- API 端点: `http://localhost:8000/api/`

## 📊 功能模块

### 用户端功能

| 功能 | 说明 |
|------|------|
| 控制台 | 请求趋势、消费统计、快速概览 |
| API 列表 | 模型展示、价格说明 |
| API 文档 | 在线文档、请求示例 |
| 我的密钥 | 创建/删除 API Key |
| 使用记录 | 请求日志、消费详情 |
| 账单充值 | 余额管理、充值记录 |
| 账户设置 | 个人信息、密码修改 |

### 管理端功能

| 功能 | 说明 |
|------|------|
| 数据总览 | 全站统计、营收概览 |
| 用户管理 | 用户列表、状态管理 |
| 模型管理 | 模型配置、价格设置 |
| 上游账户 | API 提供商配置 |
| 访问日志 | 全量请求记录查询 |
| 卡密管理 | 充值卡生成与管理 |

## 🎯 使用场景

1. **AI API 中转站** - 聚合 OpenAI、Claude、文心一言等多个 AI 提供商
2. **内部 API 网关** - 企业内部服务统一入口和鉴权
3. **API 商业化** - 快速搭建自己的 API 售卖平台
4. **API 监控分析** - 请求统计、性能监控、成本分析

## 📋 测试账号

项目提供初始化脚本 `init_test_users.py`，执行后可使用以下账号：

| 角色 | 用户名 | 密码 | 初始余额 |
|------|--------|------|---------|
| 管理员 | admin | admin123 | ¥10,000 |
| 普通用户 | testuser | test123 | ¥1,000 |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
