# 快速部署指南 - 多模输入灵感记录器

**适用于**: 立即部署到生产环境

---

## 📋 当前检查脚本输出说明

你看到的警告是**预期的** - 在开发环境运行检查脚本时会显示这些警告。

### 解读检查结果

| 检查项 | 状态 | 说明 |
|--------|------|------|
| ✗ Environment Variables | 失败 | 开发环境缺少 SECRET_KEY - **生产部署前必须配置** |
| ✓ Configuration Files | 通过 | 基础配置文件存在 |
| ✓ Database Migrations | 通过 | 1个迁移文件就绪 |
| ✓ Tests | 通过 | 14个测试文件就绪 |
| ✓ Security Configuration | 通过 | 安全设置正确 |

**⚠️ 警告说明**:
- `Missing SECRET_KEY` - 这是正常的,生产环境会通过环境变量设置
- `Optional environment variable not set` - API keys 在部署时配置
- `Optional file not found: .env.production` - 部署时会创建
- `Optional file not found: docker-compose.yml` - 已存在于项目根目录

---

## 🚀 三步部署流程

### Step 1: 生成生产环境密钥 (2分钟)

```powershell
# 在 PowerShell 中生成密钥

# 1. 生成 SECRET_KEY (最小32字符)
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# 2. 生成 ENCRYPTION_KEY (32字节)
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

**保存这些密钥** - 下一步需要使用!

---

### Step 2: 创建生产环境配置文件 (5分钟)

```powershell
# 创建 .env.production 文件
cd D:\multifuncinspirationrecord\backend
cp .env.production.example .env.production

# 设置文件权限 (Windows)
icacls .env.production /inheritance:r /grant:r "$env:USERNAME:F"
```

**编辑 .env.production 文件,填入以下必需配置**:

```bash
# ====================
# 1. 必需: 应用安全配置
# ====================
SECRET_KEY=your-generated-secret-key-from-step1
ENCRYPTION_KEY=your-generated-encryption-key-from-step1
ENVIRONMENT=production
DEBUG=false

# ====================
# 2. 必需: API Keys (获取地址见下方)
# ====================
# OpenAI API Key (https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-your-openai-api-key

# Deepgram API Key (https://console.deepgram.com/)
DEEPGRAM_API_KEY=your-deepgram-api-key

# Notion Integration (https://www.notion.so/my-integrations)
NOTION_API_KEY=secret_your-notion-integration-secret
NOTION_DATABASE_ID=your-notion-database-id

# ====================
# 3. 推荐: 错误追踪 (可选但强烈推荐)
# ====================
# Sentry DSN (https://sentry.io/)
SENTRY_DSN=https://your-key@sentry.io/your-project

# ====================
# 4. 必需: CORS 配置
# ====================
# 替换为你的实际域名
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

---

### Step 3: Docker Compose 部署 (3分钟)

```powershell
# 回到项目根目录
cd D:\multifuncinspirationrecord

# 1. 设置环境变量 (从 .env.production 读取)
# 方式A: 手动设置
$env:SECRET_KEY = "your-secret-key"
$env:OPENAI_API_KEY = "sk-your-key"
$env:DEEPGRAM_API_KEY = "your-key"
$env:NOTION_API_KEY = "secret_your-key"
$env:NOTION_DATABASE_ID = "your-db-id"
$env:SENTRY_DSN = "https://your-dsn@sentry.io/project"
$env:CORS_ORIGINS = "https://yourdomain.com"

# 方式B: 使用 .env 文件 (推荐)
# docker-compose 会自动读取项目根目录的 .env 文件
# 创建 .env 文件并复制 backend/.env.production 的内容

# 2. 启动服务
docker-compose up -d

# 3. 运行数据库迁移
docker-compose exec backend alembic upgrade head

# 4. 验证健康状态
curl http://localhost:8000/api/v1/health/readiness

# 5. 查看日志
docker-compose logs -f backend
```

---

## 🔑 API Keys 获取指南

### 1. OpenAI API Key

**用途**: AI分类和摘要生成

**获取步骤**:
1. 访问 https://platform.openai.com/signup
2. 注册/登录 OpenAI 账户
3. 进入 https://platform.openai.com/api-keys
4. 点击 "Create new secret key"
5. 复制 API key (格式: `sk-...`)

**费用**: Pay-as-you-go, GPT-3.5-turbo ~$0.002/1K tokens

---

### 2. Deepgram API Key

**用途**: 语音转文字

**获取步骤**:
1. 访问 https://console.deepgram.com/signup
2. 注册/登录 Deepgram 账户
3. 进入 https://console.deepgram.com/project/default/keys
4. 复制默认 API key 或创建新的
5. 使用该 key

**费用**: 免费 $200 credit, 之后 $0.0043/minute

---

### 3. Notion Integration

**用途**: 同步灵感记录到 Notion

**获取步骤**:
1. 访问 https://www.notion.so/my-integrations
2. 点击 "+ New integration"
3. 填写 Integration 名称 (如 "Inspiration Recorder")
4. 选择 workspace
5. 复制 "Internal Integration Secret" (格式: `secret_...`)
6. 在 Notion 中创建一个 Database
7. 在 Database 右上角点 "...", 选择 "Add connections", 添加刚创建的 Integration
8. 复制 Database ID (在 URL 中, 格式: `https://notion.so/{database_id}?v=...`)

**费用**: 免费

---

### 4. Sentry (可选但推荐)

**用途**: 错误追踪和性能监控

**获取步骤**:
1. 访问 https://sentry.io/signup/
2. 注册/登录 Sentry 账户
3. 创建新项目, 选择 "Python" / "FastAPI"
4. 复制 DSN (格式: `https://...@sentry.io/...`)

**费用**: 免费 5K events/月, Developer 计划 $26/月

---

## ✅ 部署验证清单

### 部署后立即检查

```powershell
# 1. 检查所有容器运行状态
docker-compose ps

# 预期输出:
# NAME                              STATUS
# inspiration-recorder-backend      Up (healthy)
# inspiration-recorder-redis        Up (healthy)
# inspiration-recorder-worker       Up

# 2. 检查健康端点
curl http://localhost:8000/api/v1/health/detailed

# 预期输出: 包含 "status": "healthy"

# 3. 检查日志 (无错误)
docker-compose logs --tail=50 backend

# 4. 测试基础 API
curl http://localhost:8000/api/v1/health/

# 预期输出:
# {
#   "status": "healthy",
#   "service": "inspiration-recorder-api",
#   "version": "1.0.0"
# }
```

---

## 🔍 常见问题排查

### Problem 1: SECRET_KEY 错误

**症状**: 启动失败, 日志显示 "SECRET_KEY must be at least 32 characters"

**解决**:
```powershell
# 重新生成 SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 更新环境变量
$env:SECRET_KEY = "new-generated-key"

# 重启服务
docker-compose restart backend
```

---

### Problem 2: Redis 连接失败

**症状**: 日志显示 "ConnectionRefusedError: [Errno 111] Connection refused"

**解决**:
```powershell
# 检查 Redis 容器状态
docker-compose ps redis

# 如果未运行, 启动 Redis
docker-compose up -d redis

# 检查 Redis 健康
docker-compose exec redis redis-cli ping
# 预期输出: PONG

# 重启 backend
docker-compose restart backend
```

---

### Problem 3: 数据库迁移失败

**症状**: 日志显示 "alembic.util.exc.CommandError"

**解决**:
```powershell
# 检查迁移状态
docker-compose exec backend alembic current

# 重新运行迁移
docker-compose exec backend alembic upgrade head

# 如果仍失败, 检查数据库文件权限
docker-compose exec backend ls -la data/
```

---

### Problem 4: API Key 无效

**症状**: 日志显示 "AuthenticationError: Incorrect API key"

**解决**:
1. 验证 API key 格式:
   - OpenAI: 必须以 `sk-` 开头
   - Deepgram: 32-40 个字符
   - Notion: 必须以 `secret_` 开头

2. 重新获取 API key (参考上方指南)

3. 更新环境变量并重启:
```powershell
$env:OPENAI_API_KEY = "sk-new-key"
docker-compose restart backend
```

---

## 📊 监控仪表板 (可选)

如果需要监控仪表板, 启用 Prometheus 和 Grafana:

```powershell
# 启动监控服务
docker-compose --profile monitoring up -d

# 访问服务:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
```

---

## 🔐 安全最佳实践

### 1. 保护 .env.production 文件

```powershell
# Windows - 限制文件访问
icacls backend\.env.production /inheritance:r /grant:r "$env:USERNAME:F"

# 添加到 .gitignore
echo ".env.production" >> .gitignore
```

### 2. 定期轮换密钥

- SECRET_KEY: 每 6 个月轮换一次
- API Keys: 每 3-6 个月轮换一次
- 使用 password manager 保存所有密钥

### 3. 启用 HTTPS

**生产环境必须使用 HTTPS**! 参考 `backend/DEPLOYMENT.md` 中的 Nginx 配置。

---

## 📞 支持与文档

### 完整文档

- **部署文档**: `backend/DEPLOYMENT.md` (700+ 行详细指南)
- **快速入门**: `backend/QUICKSTART.md`
- **API 文档**: http://localhost:8000/docs (部署后访问)

### 问题反馈

如遇到问题, 请检查:
1. 容器日志: `docker-compose logs backend`
2. Redis 日志: `docker-compose logs redis`
3. Worker 日志: `docker-compose logs worker`

---

## ✨ 快速命令参考

```powershell
# === 服务管理 ===
docker-compose up -d              # 启动所有服务
docker-compose down               # 停止所有服务
docker-compose restart backend    # 重启后端
docker-compose ps                 # 查看服务状态

# === 日志查看 ===
docker-compose logs -f backend    # 实时查看后端日志
docker-compose logs --tail=100    # 查看最近 100 行日志

# === 健康检查 ===
curl http://localhost:8000/api/v1/health/              # 基础健康
curl http://localhost:8000/api/v1/health/detailed      # 详细健康

# === 数据库管理 ===
docker-compose exec backend alembic current            # 当前迁移版本
docker-compose exec backend alembic upgrade head       # 运行迁移

# === 容器内操作 ===
docker-compose exec backend bash                       # 进入容器 shell
docker-compose exec redis redis-cli                    # 进入 Redis CLI

# === 清理 ===
docker-compose down -v            # 停止服务并删除 volumes
docker system prune -a            # 清理所有未使用的 Docker 资源
```

---

## 🎯 下一步

部署成功后:

1. ✅ **配置 Flutter 前端**
   - 更新 API endpoint 指向你的服务器
   - 配置 API URL: `http://your-server:8000`

2. ✅ **设置备份**
   - 配置数据库自动备份 (参考 DEPLOYMENT.md)
   - 测试恢复流程

3. ✅ **监控设置**
   - 启用 Prometheus/Grafana (可选)
   - 配置 Sentry 告警规则

4. ✅ **负载测试**
   - 使用 Apache Bench 或 Locust 进行压力测试
   - 根据结果调整 worker 数量

---

**部署完成后, 运行检查脚本验证**:

```powershell
cd backend
$env:ENVIRONMENT = "production"
python scripts/deployment_checklist.py
```

预期输出: **✓ READY FOR DEPLOYMENT** (所有检查通过)

---

**最后更新**: 2025-10-29
**适用版本**: 1.0.0
