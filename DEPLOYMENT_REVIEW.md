# Docker 部署检查与改进记录

## 已落实的改进

- Compose 统一使用根目录 `.env`，不再依赖服务器上通常不存在的 `backend/.env`。
- Redis 仅加入内部 Docker network，不再发布 `6379` 到宿主机；启动时强制使用 `REDIS_PASSWORD`，健康检查也带认证。
- Backend/Worker 等待 Redis `service_healthy` 后再启动；Prometheus/Grafana 监控端口只绑定 `127.0.0.1`。
- 生产配置启动时拒绝 `DEBUG=true`、弱 `SECRET_KEY`、`ALLOWED_HOSTS=*` 或 `ALLOWED_ORIGINS=*`。
- 主入口启用实际的限流和 50 MB 请求体限制。原先 `src.core.middleware.RateLimitMiddleware` 只是透传请求。
- `/api/v1/health/*` 不计入限流；详细健康检查正确识别 `NOTION_TOKEN`，并使用 Redis 密码连接。
- Flutter WorkManager 后台同步读取已保存的 API 地址，避免在服务器部署后把 `localhost` 当成后端。
- Flutter 默认 API 地址不再写死开发者局域网 IP，可通过 `--dart-define=API_BASE_URL=...` 注入生产地址。
- `backend/scripts/deployment_checklist.py` 现在检查实际使用的 `ALLOWED_*` 和 `NOTION_TOKEN`，并能找到根目录 Compose 文件。
- PaddleOCR 已切换到 PP-OCRv6 异步 Jobs API，支持 multipart/URL 提交、任务轮询和 JSONL 解析；详见 `PADDLEOCR_V6_MIGRATION.md`。

## 当前仍需处理的高优先级事项

1. **必须配置生产 `.env`**：至少设置随机 `SECRET_KEY`、`REDIS_PASSWORD`、`ALLOWED_HOSTS`、`ALLOWED_ORIGINS` 和实际 API key。当前工作区 `.env` 是开发配置，包含通配 Host/CORS 且 Redis 密码为空，不能直接用于服务器。
2. **SQLite 是当前真实数据库**：Compose 没有 PostgreSQL 服务，Backend 使用 `/app/data/inspirations.db`。继续使用 SQLite 时要做 `backend-data` 的定期、可恢复备份；多实例扩容前必须迁移到 PostgreSQL，并补齐 `asyncpg` 与迁移基线。
3. **迁移流程需要单独治理**：应用启动调用 `Base.metadata.create_all`，不会自动执行 Alembic。现有 `001/002` 迁移不是空库基线，不能把 `alembic upgrade head` 当作首次启动修复。上线前应建立 baseline migration，并在发布阶段显式迁移。
4. **公网入口应放在 HTTPS 反向代理后**：目前 Backend 仍发布 `8000`。建议 Nginx/Caddy 只暴露 `443`，将 `/api` 转发到 `backend:8000`，并在防火墙限制 8000 仅本机或内网。
5. **备份与恢复演练**：同时备份 `backend-data`、`backend-uploads`、`backend-logs`（日志可按保留策略清理），至少验证一次从备份恢复后健康检查和记录读取。
6. **API 当前没有真正的用户认证/授权依赖**：记录、偏好和同步接口没有统一的 `Authorization` 校验。如果 8000 端口或反向代理对公网开放，任何人都可能读写数据；上线前至少加 API token/OIDC，并按用户隔离记录。
7. **限流仍是单进程内存实现**：Compose 使用 4 个 Uvicorn worker 时，每个进程都有独立计数器，不能形成全局限流。高流量或公网场景应把计数迁移到 Redis，并在反向代理再加一层限流。
8. **PaddleOCR Token 需要轮换**：本次真实验证使用了你提供的 Token，且旧配置 Token 返回 `401`。请在 PaddleOCR 控制台生成/确认新 Token 后，仅写入服务器 `.env`，不要提交仓库。

## 推荐部署命令

```bash
cp .env.example .env
# 编辑 .env，填写生产值；ALLOWED_* 不要使用 '*'
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl -f http://127.0.0.1:8000/api/v1/health/readiness
docker compose logs --tail=100 backend worker
```

客户端构建示例：

```bash
flutter build apk --release --dart-define=API_BASE_URL=https://api.example.com
```

监控服务按需启用：

```bash
docker compose --profile monitoring up -d
```

## 验证结果

- `docker compose config --quiet`：使用临时非通配 `ALLOWED_*` 和非空 Redis 密码覆盖后通过。
- `python -m compileall backend/src`：通过。
- Flutter `analyze`：项目当前已有约 1000 个 lint/info/error（主要集中在未生成 mock、失配的测试组件和既有风格问题），本次改动未新增可见编译错误；应另开任务清理测试基线。
- 本机未安装可用的 Python `pytest`，未能执行后端测试套件；服务器上线前应在镜像或虚拟环境中执行 `pytest`。
