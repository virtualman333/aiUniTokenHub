# uniTokenHub

聚合API接口中转服务

## 项目简介

uniTokenHub 是一个聚合API接口中转服务系统，提供统一的API网关功能，支持：
- API统一管理
- 密钥认证
- 请求限流
- 使用统计
- 用户管理

## 技术栈

### 后端
- Django 4.2+
- Django REST Framework
- PostgreSQL
- Redis

### 前端
- Vue 3 + Composition API
- Element Plus
- Pinia
- Vue Router

## 项目结构

```
uniTokenHub.ai/
├── backend/              # Django后端
│   ├── apps/
│   │   ├── users/        # 用户管理
│   │   ├── api_proxy/    # API代理
│   │   └── dashboard/    # 仪表盘
│   ├── config/           # 配置文件
│   ├── manage.py
│   └── requirements.txt
│
├── frontend/             # Vue3前端
│   ├── src/
│   │   ├── layouts/      # 布局组件
│   │   ├── views/       # 页面视图
│   │   ├── stores/      # 状态管理
│   │   └── router/      # 路由配置
│   ├── package.json
│   └── vite.config.js
│
├── README.md
└── LICENSE
```

## 快速开始

### 后端

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
# 编辑 .env 文件

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建管理员
python manage.py createsuperuser

# 运行服务
python manage.py runserver
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

## 配置说明

### 数据库配置 (.env)


## API文档

启动后端服务后访问：
- 管理后台: http://localhost:8000/admin/
- API端点: http://localhost:8000/api/

## 许可证

MIT License
📋 测试账号
角色	用户名	密码	余额
管理员	admin	admin123	¥10,000
普通用户	testuser	test123	¥1,000
