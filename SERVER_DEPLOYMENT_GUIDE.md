# 服务器端 Docker 部署指南

本指南介绍如何在服务器上使用 Docker Compose 部署 Multimodal Inspiration Recorder。

## 目录

- [环境要求](#环境要求)
- [快速部署](#快速部署)
- [详细步骤](#详细步骤)
- [配置说明](#配置说明)
- [服务管理](#服务管理)
- [监控与日志](#监控与日志)
- [备份与恢复](#备份与恢复)
- [故障排查](#故障排查)
- [安全建议](#安全建议)

---

## 环境要求

### 硬件要求
- **CPU**: 2核以上
- **内存**: 4GB 以上 (推荐 8GB)
- **存储**: 20GB 以上可用空间
- **网络**: 稳定的互联网连接

### 软件要求
- **操作系统**: Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+) 或其他支持 Docker 的系统
- **Docker**: 20.10+ 版本
- **Docker Compose**: 2.0+ 版本

### 外部服务依赖
- **Deepgram API**: 语音转文本服务
- **PaddleOCR-VL API**: 图片 OCR 识别服务
- **OpenRouter API**: AI 内容处理服务
- **Notion API**: (可选) Notion 同步服务

---

## 快速部署

```bash
# 1. 克隆仓库
git clone https://github.com/hegonghao/multimodal-inspiration-recorder.git
cd multimodal-inspiration-recorder

# 2. 切换到正确的分支
git checkout 1-multimodal-capture

# 3. 复制环境变量模板
cp .env.example .env

# 4. 编辑环境变量 (必须配置)
nano .env
# 或使用 vim
vim .env

# 5. 启动所有服务
docker-compose up -d

# 6. 查看服务状态
docker-compose ps

# 7. 查看日志
docker-compose logs -f
```

---

## 详细步骤

### 1. 安装 Docker 和 Docker Compose

#### Ubuntu/Debian
```bash
# 更新包索引
sudo apt-get update

# 安装必要的依赖
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加 Docker 官方 GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 设置稳定版仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
docker compose version
```

#### CentOS/RHEL
```bash
# 安装必要的依赖
sudo yum install -y yum-utils

# 添加 Docker 仓库
sudo yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker Engine
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
docker compose version
```

### 2. 克隆项目仓库

```bash
# 克隆仓库
git clone https://github.com/hegonghao/multimodal-inspiration-recorder.git
cd multimodal-inspiration-recorder

# 切换到开发分支
git checkout 1-multimodal-capture

# 查看项目结构
ls -la
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

#### 必须配置的环境变量

```bash
# ================================
# 数据库配置
# ================================
POSTGRES_DB=inspiration_recorder
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here  # 修改为强密码
POSTGRES_HOST=db
POSTGRES_PORT=5432

# ================================
# Redis 配置
# ================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password_here  # 修改为强密码

# ================================
# API 密钥配置 (必须)
# ================================
# Deepgram API - 语音转文本
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# PaddleOCR API - 图片 OCR
PADDLEOCR_API_URL=https://paddleocr.aistudio-app.com/api/v2/ocr/jobs
PADDLEOCR_TOKEN=your_paddleocr_token_here

# OpenRouter API - AI 处理
OPENROUTER_API_KEY=your_openrouter_api_key_here

# ================================
# Notion 同步配置 (可选)
# ================================
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id

# ================================
# 应用配置
# ================================
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=your_secret_key_here  # 生成随机密钥

# ================================
# Sentry 监控 (可选)
# ================================
SENTRY_DSN=your_sentry_dsn_here
```

#### 生成安全密钥

```bash
# 生成随机 SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 生成强密码
openssl rand -base64 32
```

### 4. 构建并启动服务

```bash
# 拉取并构建所有镜像
docker-compose build

# 启动所有服务 (后台运行)
docker-compose up -d

# 查看启动日志
docker-compose logs -f

# 只查看特定服务的日志
docker-compose logs -f backend
docker-compose logs -f worker
```

### 5. 初始化数据库

```bash
# 进入后端容器
docker exec -it inspiration-recorder-backend bash

# 运行数据库迁移
alembic upgrade head

# 退出容器
exit
```

### 6. 验证部署

```bash
# 检查所有服务状态
docker-compose ps

# 应该看到所有服务都是 "Up" 状态:
# - db (PostgreSQL)
# - redis
# - backend (FastAPI)
# - worker (ARQ Worker)

# 测试后端 API
curl http://localhost:8000/api/v1/health

# 应该返回:
# {"status":"healthy","timestamp":"2025-11-10T..."}

# 测试数据库连接
docker exec -it inspiration-recorder-backend python -c "from src.database import get_db; print('Database connected!')"
```

---

## 配置说明

### docker-compose.yml 结构

```yaml
services:
  # PostgreSQL 数据库
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"

  # Redis 缓存
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  # FastAPI 后端
  backend:
    build: ./backend
    volumes:
      - ./backend:/app
      - ./data:/data
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      - db
      - redis
    ports:
      - "8000:8000"

  # ARQ Worker (后台任务)
  worker:
    build: ./backend
    command: arq src.app.worker.WorkerSettings
    volumes:
      - ./backend:/app
      - ./data:/data
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      - db
      - redis
```

### 端口映射

| 服务 | 容器端口 | 主机端口 | 用途 |
|------|---------|---------|------|
| backend | 8000 | 8000 | FastAPI REST API |
| db | 5432 | 5432 | PostgreSQL 数据库 |
| redis | 6379 | 6379 | Redis 缓存 |

如果端口冲突,可以修改主机端口:
```yaml
ports:
  - "8001:8000"  # 将主机 8001 端口映射到容器 8000 端口
```

---

## 服务管理

### 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 启动特定服务
docker-compose up -d backend
docker-compose up -d worker

# 不使用缓存重新构建
docker-compose up -d --build

# 强制重新创建容器
docker-compose up -d --force-recreate
```

### 停止服务

```bash
# 停止所有服务
docker-compose stop

# 停止特定服务
docker-compose stop backend
docker-compose stop worker

# 停止并移除容器 (数据卷不会删除)
docker-compose down

# 停止并移除容器及数据卷 (危险操作!)
docker-compose down -v
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
docker-compose restart worker
```

### 更新服务

```bash
# 拉取最新代码
git pull origin 1-multimodal-capture

# 重新构建并启动
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 运行数据库迁移 (如果有变更)
docker exec -it inspiration-recorder-backend alembic upgrade head
```

---

## 监控与日志

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 实时查看日志 (跟随模式)
docker-compose logs -f

# 查看特定服务日志
docker-compose logs backend
docker-compose logs worker

# 查看最近 100 行日志
docker-compose logs --tail=100

# 查看带时间戳的日志
docker-compose logs -t
```

### 查看服务状态

```bash
# 查看所有容器状态
docker-compose ps

# 查看容器资源使用情况
docker stats

# 查看特定容器详细信息
docker inspect inspiration-recorder-backend
```

### 进入容器调试

```bash
# 进入后端容器
docker exec -it inspiration-recorder-backend bash

# 进入数据库容器
docker exec -it inspiration-recorder-db psql -U postgres -d inspiration_recorder

# 进入 Redis 容器
docker exec -it inspiration-recorder-redis redis-cli -a your_redis_password
```

---

## 备份与恢复

### 数据库备份

```bash
# 创建备份目录
mkdir -p ./backups

# 备份数据库
docker exec inspiration-recorder-db pg_dump -U postgres inspiration_recorder > ./backups/backup_$(date +%Y%m%d_%H%M%S).sql

# 压缩备份
gzip ./backups/backup_$(date +%Y%m%d_%H%M%S).sql
```

### 数据库恢复

```bash
# 解压备份文件
gunzip ./backups/backup_20251110_120000.sql.gz

# 恢复数据库
docker exec -i inspiration-recorder-db psql -U postgres inspiration_recorder < ./backups/backup_20251110_120000.sql
```

### 自动备份脚本

创建 `backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"

# 创建备份目录
mkdir -p ${BACKUP_DIR}

# 备份数据库
docker exec inspiration-recorder-db pg_dump -U postgres inspiration_recorder > ${BACKUP_FILE}

# 压缩备份
gzip ${BACKUP_FILE}

# 删除 7 天前的备份
find ${BACKUP_DIR} -name "backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

设置定时任务 (crontab):
```bash
# 编辑 crontab
crontab -e

# 添加每天凌晨 2 点自动备份
0 2 * * * /path/to/multimodal-inspiration-recorder/backup.sh
```

---

## 故障排查

### 1. 服务无法启动

#### 检查端口占用
```bash
# 检查端口是否被占用
sudo netstat -tulpn | grep -E '8000|5432|6379'

# 或使用 lsof
sudo lsof -i :8000
sudo lsof -i :5432
sudo lsof -i :6379
```

解决方法:
- 停止占用端口的程序
- 或修改 `docker-compose.yml` 中的端口映射

#### 检查 Docker 服务
```bash
# 检查 Docker 服务状态
sudo systemctl status docker

# 重启 Docker 服务
sudo systemctl restart docker
```

### 2. 数据库连接失败

```bash
# 检查数据库容器日志
docker-compose logs db

# 检查环境变量
docker exec inspiration-recorder-backend env | grep POSTGRES

# 测试数据库连接
docker exec -it inspiration-recorder-db psql -U postgres -d inspiration_recorder
```

### 3. API 请求失败

```bash
# 检查后端日志
docker-compose logs backend

# 检查后端容器状态
docker-compose ps backend

# 测试 API 端点
curl http://localhost:8000/api/v1/health

# 检查环境变量配置
docker exec inspiration-recorder-backend python check_config.py
```

### 4. Worker 任务不执行

```bash
# 检查 Worker 日志
docker-compose logs worker

# 检查 Redis 连接
docker exec inspiration-recorder-backend python -c "import redis; r = redis.from_url('redis://:password@redis:6379/0'); print(r.ping())"

# 查看 ARQ 队列状态
docker exec inspiration-recorder-backend python -c "from arq import create_pool; import asyncio; asyncio.run(create_pool('redis://:password@redis:6379/0'))"
```

### 5. 磁盘空间不足

```bash
# 查看磁盘使用情况
df -h

# 查看 Docker 空间使用
docker system df

# 清理未使用的镜像、容器、网络
docker system prune -a

# 清理未使用的数据卷 (谨慎!)
docker volume prune
```

### 6. 内存不足

```bash
# 查看容器内存使用
docker stats

# 限制容器内存使用 (在 docker-compose.yml 中)
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
```

---

## 安全建议

### 1. 环境变量安全

- ✅ 使用强密码 (至少 16 位,包含大小写字母、数字、特殊字符)
- ✅ 不要在代码中硬编码敏感信息
- ✅ 定期轮换 API 密钥和密码
- ✅ 使用密钥管理服务 (如 AWS Secrets Manager, HashiCorp Vault)

### 2. 网络安全

```bash
# 使用防火墙限制访问
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 5432/tcp   # 禁止外部访问数据库
sudo ufw deny 6379/tcp   # 禁止外部访问 Redis
sudo ufw enable
```

### 3. HTTPS 配置

使用 Nginx 反向代理 + Let's Encrypt SSL 证书:

```nginx
# /etc/nginx/sites-available/inspiration-recorder
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. 定期更新

```bash
# 更新系统包
sudo apt-get update && sudo apt-get upgrade -y

# 更新 Docker 镜像
docker-compose pull
docker-compose up -d

# 更新应用代码
git pull origin 1-multimodal-capture
docker-compose build --no-cache
docker-compose up -d
```

### 5. 日志审计

```bash
# 启用 Docker 日志驱动
# 在 docker-compose.yml 中添加:
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 性能优化

### 1. 数据库优化

```sql
-- 创建索引 (在数据库容器中执行)
CREATE INDEX idx_records_created_at ON inspiration_records(created_at);
CREATE INDEX idx_records_user_id ON inspiration_records(user_id);
CREATE INDEX idx_sync_queue_status ON sync_queue(status);
```

### 2. Redis 持久化

```yaml
# docker-compose.yml
redis:
  command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
```

### 3. 资源限制

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

---

## 监控告警

### 使用 Sentry 监控

1. 注册 Sentry 账号: https://sentry.io
2. 创建新项目
3. 获取 DSN
4. 在 `.env` 中配置:
```bash
SENTRY_DSN=your_sentry_dsn_here
```

### 健康检查端点

```bash
# 定期检查服务健康状态
curl http://localhost:8000/api/v1/health

# 使用监控工具 (如 UptimeRobot, Pingdom)
```

---

## 常用命令速查

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps

# 进入容器
docker exec -it inspiration-recorder-backend bash

# 备份数据库
docker exec inspiration-recorder-db pg_dump -U postgres inspiration_recorder > backup.sql

# 恢复数据库
docker exec -i inspiration-recorder-db psql -U postgres inspiration_recorder < backup.sql

# 清理系统
docker system prune -a

# 更新服务
git pull && docker-compose build && docker-compose up -d
```

---

## 联系支持

如有问题,请通过以下方式联系:

- **GitHub Issues**: https://github.com/hegonghao/multimodal-inspiration-recorder/issues
- **项目文档**: 查看 `backend/DEPLOYMENT.md` 和 `README.md`

---

**部署完成后,记得:**
1. ✅ 修改所有默认密码
2. ✅ 配置防火墙规则
3. ✅ 设置 HTTPS
4. ✅ 配置自动备份
5. ✅ 启用监控告警
6. ✅ 定期更新系统和应用
