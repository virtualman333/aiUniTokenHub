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

## API文档
启动服务后访问: http://localhost:8000/admin/
