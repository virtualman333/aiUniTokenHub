# uniTokenHub

开箱即用的 API 中转站框架 / 统一 API 网关服务
官网:https://unitokenhub.m3it.cn/

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

上面只列了主要目录。`apps/` 下还有 `dashboard/`（数据看板、余额续航预测）、`image_gen/`（图像生成）、`tickets/`、`utils/`；各应用自己的单元测试放在 `apps/应用名/tests/` 下，统一用 `backend/run_tests.py` 跑。

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 5.7+
- Redis 6+

> 数据库口径以 `backend/config/settings.py` 的 `REQUIRED_DATABASE` 为准（代码里专门绕过了 Django 的版本检查来兼容 5.7，所以别把它写成 8+，也不必去装别的数据库）。

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

### 2. 单元测试

```bash
cd backend

# 跑全部后端单元测试（不需要数据库，也不需要 .env）
python run_tests.py
```

后端单元测试是**纯 Python** 的：不连数据库、不读 Django settings。计费口径、OpenAI/Anthropic 协议转换、流式状态机、图像定价规则这些最贵也最容易悄悄改坏的地方，都靠这一层锁住。相关的几条硬规则：

- **定价格只允许有一个来源**：图像单张价格（含「模型没配单价时用多少」）在 `apps/image_gen/pricing.py`；`chatcmpl… → resp…` 的 id 映射在 `apps/api_proxy/adapters/ids.py`，流式与非流式共用。别在 `views.py` 里再写一遍。
- **扣费必须是原子的**：`transaction.atomic()` + `select_for_update()`，余额在锁内重读；图片生成要**先扣费再保存图片**，否则一次「余额不足」的请求会把图留在库里，用户照样能下载。
- **扣了钱没给货必须退**：正因为是先扣费再保存图片，保存图片失败（磁盘/COS 写不进去）就得原路退回、并写一条 `type='refund'` 账单，退完把本次 `cost` 归零当幂等标记。退款和扣费要拿同一把锁、顺序也一致（先 `User` 再 `ImageGeneration`），否则并发下会互相等锁。退款本身失败时不抛异常 —— 已经是最坏的情况，该如实写进日志和返回信息说「没退成」，而不是再抛一个异常把真正的失败原因盖掉。
- **扣费失败的原因要分档**：`_deduct_cost()` 与 `calculate_and_deduct_cost()` 都返回 `(cost, DEDUCT_OK | DEDUCT_INSUFFICIENT | DEDUCT_ERROR)` 三档结果，不再是布尔值。服务端自己出错（查库/写库异常）不能报成「余额不足」—— 那会诱导用户去充值，还把 500 伪装成 400 让人以为是请求写错了。所有面向用户的计费文案（余额不足、扣费失败、退款到账/未到账）、以及失败时的 HTTP 状态码与错误 `code`，都由 `apps/utils/billing.py` 生成，别在 `views.py` 里另写一份。
- **两条扣费路径的「余额不足」不同源，且是有意的**：图片路径允许 `DEDUCT_INSUFFICIENT`（前置校验按 `balance < cost` 判）；LLM 路径（`/v1/chat/completions` 与 `/v1/responses`）的扣费**允许把余额扣成负数**，好让已经花掉上游成本的那一笔照样记账，透支由下一次请求入口的 `balance <= 0` 拦住 —— 所以那条路径上扣费失败**只可能是服务端出错**，报「余额不足」一定是假话。入口那道前置校验才可以说「余额不足」，因为它判的是事实。
- **流式请求必须主动向上游索取 usage**：OpenAI 兼容协议里，流式响应**默认一个 chunk 都不带 `usage`** —— 要拿到它，请求必须带 `stream_options.include_usage = true`。请求体只由 `apps/api_proxy/adapters/upstream_body.py` 拼装（`/v1/chat/completions` 与 `/v1/responses` 两条流式端点共用它），别再自己写 `body['stream'] = True`。少了这个字段，收尾计费那句 `if total_tokens > 0` 会**整段跳过扣费**：余额不动、用量记为 0、账单里没有这一笔，而且不报错 —— 与「这次调用真的免费」完全一样。所以收尾时若「成功但一个 token 都没收到」，会由 `billing.unbilled_stream_note()` 记一条 WARNING，让「这笔没收钱」至少留下痕迹。Anthropic 的流自带 usage（`message_start` / `message_delta`），而且它不认 `stream_options`，所以这个字段只对 OpenAI 协议加。

> 为什么文案模块在 `apps/utils/` 而不是 `apps/image_gen/`：它现在服务三条路径（图片、chat/completions、responses）。`apps/utils/__init__.py` 因此**不做任何 re-export** —— 一旦在里面 `from .response import ...`，`from apps.utils import billing` 就会连带把 Django/DRF 拖进来，纯 Python 测试立刻跑不起来。

`run_tests.py` 扫的是 `apps/*/tests/`，不是写死的清单 —— 清单必然会漂移：`apps/dashboard/` 没有 `__init__.py`，`python -m unittest discover -s apps -t .` 会**不报错地**跳过整个包，曾有 21 个用例因此长期没被跑过。现在某个 `tests/` 目录缺 `__init__.py` 就会直接失败，不允许静默少跑。另外，有 `test_*.py` 掉在收集范围之外、或某个包一条用例都没收到，也会直接失败；这两道自证写在 `run_tests.py` 自己里，不能只放在 `apps/docs/tests/` —— 那里的用例本身就在被扫的范围内，扫描面一收窄它们跟着一起消失（实测：把收集清单换成写死的单包，全仓从 296 例悄悄变成 116 例，输出仍是 `OK`）。

### 3. 前端部署

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

`npm run build` 跑的是 `vite build && node scripts/zip-dist.js`，**一次就把两件事都做了**：产出 `frontend/dist/`，并打成 `frontend/dist.zip`（两个都在 `.gitignore` 里）。想单独预览构建结果用 `npm run preview`。

前端脚本清单以 `frontend/package.json` 的 `scripts` 为准 —— 文档里写下的每条 `npm run` 命令是否真实存在，由 `backend/apps/docs/tests/test_docs_contract.py` 检查（此前这里写着 `npm run build:zip`，而那个脚本从来没有过，照抄只会得到 `Missing script`）。

## 🔧 配置说明

### 环境变量 (.env)

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DEBUG | 调试模式 | True |
| SECRET_KEY | Django 密钥 | dev-secret-key-change-in-production |
| DB_NAME | 数据库名 | ********* |
| DB_USER | 数据库用户名 | ********* |
| DB_PASSWORD | 数据库密码 | ********* |
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
| 充值管理 | 充值渠道与套餐配置 |

## 🎯 使用场景

1. **AI API 中转站** - 聚合 OpenAI、Claude、文心一言等多个 AI 提供商
2. **内部 API 网关** - 企业内部服务统一入口和鉴权
3. **API 商业化** - 快速搭建自己的 API 售卖平台
4. **API 监控分析** - 请求统计、性能监控、成本分析

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
