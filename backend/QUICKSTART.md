# Backend Quickstart Guide

> **⚠️ 架构说明**: 本项目当前有两个应用入口点 (`src/main.py` 和 `src/api/main.py`)。本快速开始指南使用 **`src/main.py`** 作为主入口点。详见 [`docs/quickstart_validation_report.md`](docs/quickstart_validation_report.md)。

## 1. 安装依赖

确保你在 `myenv` 虚拟环境中：

```bash
# 激活虚拟环境 (如果未激活)
conda activate myenv

# 安装所有依赖
cd backend
pip install -r requirements.txt
```

## 2. 配置环境变量

```bash
# 复制示例配置文件
cp .env.example .env

# (可选) 编辑 .env 文件配置高级选项
# 开发环境：SECRET_KEY 有安全的默认值，无需配置
# 生产环境：必须设置自定义 SECRET_KEY
```

**开发环境**: 配置有安全的默认值，可以直接使用

**生产环境**: 必须在 `.env` 中设置以下环境变量：
```bash
ENVIRONMENT=production
SECRET_KEY=your-secret-key-at-least-32-characters-long
```

## 3. 初始化数据库

数据库会在首次启动时自动创建。确保 `data` 目录存在：

```bash
mkdir -p data
```

## 4. 启动后端服务

### 方式一：使用 uvicorn 直接启动

```bash
cd backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 方式二：使用 Python 运行

```bash
cd backend
python -m src.main
```

服务将在 `http://localhost:8000` 启动

## 5. 验证服务

在浏览器访问：

- **Health Check**: http://localhost:8000/health
- **API 文档**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 6. (可选) 启动 ARQ Worker 用于 Notion 同步

如果需要 Notion 同步功能：

```bash
# 新开一个终端
cd backend
arq src.app.worker.WorkerSettingsClass
```

## 常见问题

### 问题 1: ModuleNotFoundError

**错误**: `ModuleNotFoundError: No module named 'fastapi'`

**解决**: 确保安装了所有依赖
```bash
pip install -r requirements.txt
```

### 问题 2: 数据库连接错误

**错误**: `Database connection failed`

**解决**: 确保 `data` 目录存在
```bash
mkdir -p data
```

### 问题 3: Redis 连接失败

**错误**: `Redis connection refused`

**解决**:
- 如果不使用 Notion 同步，可以忽略此错误
- 如果需要同步，安装并启动 Redis:
  ```bash
  # Windows (使用 WSL)
  sudo service redis-server start

  # macOS
  brew services start redis

  # Docker
  docker run -d -p 6379:6379 redis:alpine
  ```

### 问题 4: 生产环境 SECRET_KEY 配置

**开发环境**: 无需配置，使用默认值

**生产环境必须配置**: 设置 `ENVIRONMENT=production` 时，必须提供自定义 SECRET_KEY

**错误**: `Production environment requires a secure SECRET_KEY`

**解决**: 在 `.env` 文件中设置 SECRET_KEY
```bash
echo "ENVIRONMENT=production" >> .env
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env
```

或手动编辑 `.env` 文件添加至少32字符的密钥。

## API 端点概览

### 灵感记录相关
- `POST /api/v1/records/` - 创建记录 (支持语音/图片/文字)
- `GET /api/v1/records/` - 获取记录列表
- `GET /api/v1/records/{id}` - 获取单个记录
- `PUT /api/v1/records/{id}` - 更新记录
- `DELETE /api/v1/records/{id}` - 删除记录

### Notion 同步相关
- `GET /api/v1/sync/status` - 获取同步状态
- `POST /api/v1/sync/trigger` - 触发手动同步
- `GET /api/v1/sync/queue` - 查看同步队列
- `POST /api/v1/sync/retry-failed` - 重试失败的同步任务

### AI 处理相关
- `POST /api/v1/ai/classify` - 分类文本
- `POST /api/v1/ai/summarize` - 生成摘要

### 用户偏好设置
- `GET /api/v1/preferences/` - 获取用户设置
- `PUT /api/v1/preferences/` - 更新用户设置

## 下一步

1. 测试 API 端点
2. 配置 Notion Integration (如果需要)
3. 配置 AI 服务 (Ollama/OpenAI)
4. 启动 Flutter 前端应用
