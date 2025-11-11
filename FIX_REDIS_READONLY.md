# Redis 只读错误修复指南

## 🔴 问题现象

Worker 启动时报错：

```
redis.exceptions.ReadOnlyError: You can't write against a read only replica.
```

ARQ Worker 无法启动，后台任务（如 AI 处理、Notion 同步）无法执行。

---

## 🎯 根本原因

Redis 被错误配置为**只读副本（read-only replica）**，可能原因：

1. **数据卷持久化问题**：Redis 数据目录保留了之前的副本配置
2. **主从复制配置错误**：Redis 被误配置为从节点
3. **容器重启后状态异常**：Redis 启动时加载了错误的配置

---

## 🛠️ 修复步骤

### 步骤 1：诊断 Redis 状态

```bash
# 1. 检查 Redis 角色
docker exec inspiration-recorder-redis redis-cli INFO replication | grep role

# 2. 检查是否是只读副本
docker exec inspiration-recorder-redis redis-cli CONFIG GET replica-read-only

# 3. 检查主从复制配置
docker exec inspiration-recorder-redis redis-cli INFO replication
```

**正常输出**：
```
role:master
replica-read-only:yes
```

**异常输出**：
```
role:slave
# 或
role:replica
```

---

### 步骤 2：快速修复（无需重启）

#### 方法 A：移除副本配置（推荐）

如果 Redis 角色是 `slave` 或 `replica`：

```bash
# 移除主从复制关系，设置为主节点
docker exec inspiration-recorder-redis redis-cli REPLICAOF NO ONE

# 验证
docker exec inspiration-recorder-redis redis-cli INFO replication | grep role
# 应该显示: role:master

# 测试写入
docker exec inspiration-recorder-redis redis-cli SET test_key "success"
docker exec inspiration-recorder-redis redis-cli GET test_key
# 应该返回: "success"
```

#### 方法 B：禁用只读模式

如果角色是 `master` 但仍然只读：

```bash
# 禁用只读模式
docker exec inspiration-recorder-redis redis-cli CONFIG SET replica-read-only no

# 验证
docker exec inspiration-recorder-redis redis-cli CONFIG GET replica-read-only
# 应该显示: replica-read-only: no
```

---

### 步骤 3：重启 Worker

```bash
# 重启 worker 服务
docker-compose restart worker

# 查看 worker 日志
docker-compose logs -f worker
```

**预期日志**：
```
09:xx:xx: Starting worker for 2 functions: sync_inspiration_to_notion, cron:scheduled_sync_check
09:xx:xx: redis_version=7.4.7 mem_usage=1.60M clients_connected=1 db_keys=8
arq_worker_starting
```

**不应该再看到**：
```
❌ redis.exceptions.ReadOnlyError: You can't write against a read only replica.
```

---

### 步骤 4：持久化配置（可选）

如果希望配置持久化到 Redis 配置文件：

```bash
# 保存当前配置到磁盘
docker exec inspiration-recorder-redis redis-cli CONFIG REWRITE
```

---

## 🔄 彻底清理方案（如果快速修复无效）

如果 Redis 数据卷损坏或配置持续错误，需要清理数据卷：

⚠️ **警告**：此操作会删除 Redis 中的所有数据（包括任务队列、缓存）。后端数据库（SQLite）不受影响。

```bash
# 1. 停止所有服务
docker-compose down

# 2. 删除 Redis 数据卷
docker volume rm multimodal-inspiration-recorder_redis-data

# 或者如果名称不同
docker volume ls | grep redis
docker volume rm <redis-volume-name>

# 3. 重新启动服务
docker-compose up -d redis backend worker

# 4. 验证 Redis 角色
docker exec inspiration-recorder-redis redis-cli INFO replication | grep role
# 应该显示: role:master

# 5. 测试写入
docker exec inspiration-recorder-redis redis-cli SET test "ok"
docker exec inspiration-recorder-redis redis-cli GET test
# 应该返回: "ok"

# 6. 查看 worker 日志
docker-compose logs -f worker
```

---

## 📊 验证修复成功

### 1. Redis 状态检查

```bash
# 角色应该是 master
docker exec inspiration-recorder-redis redis-cli INFO replication | grep role
# 输出: role:master

# 可以写入
docker exec inspiration-recorder-redis redis-cli SET health_check "$(date)"
docker exec inspiration-recorder-redis redis-cli GET health_check
```

### 2. Worker 状态检查

```bash
# Worker 应该正常运行
docker-compose ps worker
# State 应该是 "Up"

# 日志无错误
docker-compose logs worker | grep -i error | tail -10
# 应该没有 ReadOnlyError
```

### 3. 任务队列测试

在手机 App 上测试：
1. 创建一条语音记录
2. 检查是否自动处理（生成标题、分类）
3. 检查后端日志：
   ```bash
   docker-compose logs -f backend | grep -E "AI processing|task enqueued"
   ```

---

## 🔍 故障排查

### 问题 1：修复后仍然是副本

**可能原因**：Redis 配置文件或数据持久化文件包含副本配置

**解决方法**：
```bash
# 1. 检查 Redis 配置
docker exec inspiration-recorder-redis cat /usr/local/etc/redis/redis.conf | grep replicaof

# 2. 如果有 replicaof 配置，需要清理数据卷
docker-compose down
docker volume rm multimodal-inspiration-recorder_redis-data
docker-compose up -d
```

---

### 问题 2：修复后 Worker 仍然报错

**可能原因**：Worker 缓存了旧的 Redis 连接

**解决方法**：
```bash
# 1. 重启 worker 和 backend
docker-compose restart backend worker

# 2. 如果问题持续，重新构建容器
docker-compose down
docker-compose build backend worker
docker-compose up -d
```

---

### 问题 3：修复后 Redis 数据丢失

**说明**：如果使用了清理数据卷的方法，Redis 中的数据会被清除，包括：
- ARQ 任务队列
- 缓存数据

**影响**：
- ✅ 后端数据库（SQLite）**不受影响**，所有灵感记录完好
- ⚠️ 正在排队的后台任务会丢失，需要重新触发
- ⚠️ 缓存数据会清空，首次访问可能稍慢

**恢复方法**：
在手机 App 上触发同步，重新入队任务：
```bash
# 或者在后端触发全量同步
docker exec inspiration-recorder-backend python -c "
from src.services.sync_service import SyncService
import asyncio
asyncio.run(SyncService().trigger_sync())
"
```

---

## 🔧 预防措施

### 1. 避免手动配置主从复制

除非明确需要 Redis 主从架构，否则不要运行：
```bash
❌ redis-cli REPLICAOF <master-ip> <master-port>
```

### 2. 定期备份 Redis 数据（可选）

如果需要保留 Redis 数据：
```bash
# 手动触发 RDB 快照
docker exec inspiration-recorder-redis redis-cli BGSAVE

# 备份 RDB 文件
docker cp inspiration-recorder-redis:/data/dump.rdb ./redis-backup-$(date +%Y%m%d).rdb
```

### 3. 监控 Redis 状态

添加到监控脚本：
```bash
#!/bin/bash
ROLE=$(docker exec inspiration-recorder-redis redis-cli INFO replication | grep role | cut -d: -f2 | tr -d '\r')
if [ "$ROLE" != "master" ]; then
    echo "⚠️ WARNING: Redis role is $ROLE (expected: master)"
    # 自动修复
    docker exec inspiration-recorder-redis redis-cli REPLICAOF NO ONE
fi
```

---

## 📚 相关文档

- **DOCKER_ENV_FIX.md** - Docker 环境变量问题修复
- **FIX_LLM_API_CONNECTION.md** - LLM API 连接问题修复
- **SERVER_DEPLOYMENT_GUIDE.md** - 完整服务器部署指南

---

## 📞 技术支持

如果问题持续：

1. **收集诊断信息**：
   ```bash
   docker exec inspiration-recorder-redis redis-cli INFO > redis-info.txt
   docker-compose logs redis > redis.log
   docker-compose logs worker > worker.log
   ```

2. **在 GitHub 提 Issue**：
   - 附上 `redis-info.txt`
   - 附上 `worker.log`（最后 100 行）
   - 说明已尝试的修复步骤

**GitHub Issues**: https://github.com/hegonghao/multimodal-inspiration-recorder/issues
