# uniTokenHub 后端

## 环境要求
- Python 3.10+
- MySQL 8+
- Redis 6+

## 安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库和Redis

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建管理员账号
python manage.py createsuperuser

# 运行服务器
python manage.py runserver
```

## 测试

`apps/api_proxy/tests/` 是协议适配层（OpenAI ↔ Anthropic 转换）与流式转换状态机的单元测试。
纯 Python，**不需要数据库、不需要 Django settings**，秒级跑完：

```bash
cd backend
python -m unittest discover -s apps/api_proxy/tests -t . -v
```

两组重点：

- **计费口径**：`anthropic_to_openai` 必须把 `cache_creation_input_tokens` 与
  `cache_read_input_tokens` 一并计入 `prompt_tokens`，否则缓存命中会漏计费。
- **流式正确性**：`streaming_adapter.py` 的两个状态机（Chat Completions → Response API、
  Anthropic → Chat Completions）。这里锁住三条容易回归的约束：多字节字符跨 chunk 不得被切坏
  （所以必须用 `IncrementalUtf8Decoder`，不能 `chunk.decode(..., errors='replace')`）、
  `response.completed.output` 的顺序必须与公布的 `output_index` 一致、标准流下收尾事件只能发一次。

改动 `apps/api_proxy/adapters/` 或 `views_openai.py` / `views_responses.py` 的流式分支后都应跑通这组测试。

## API文档
启动服务后访问: http://localhost:8000/admin/
