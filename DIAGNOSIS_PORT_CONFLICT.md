# App无法连接到Backend - 问题诊断报告

## 根本原因

**端口冲突：8000端口被两个服务同时占用！**

### 当前状态

1. **Docker Backend容器**：正确运行，但无法接收外部请求
2. **本地Python进程 (PID 29988)**：占用了8000端口，但使用错误的入口点

```bash
PID 29988: "C:\Python312\python.exe" -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 问题表现

- ✅ `curl http://localhost:8000/api/v1/health/liveness` → 工作正常（本地Python）
- ❌ `curl http://192.168.13.222:8000/api/v1/health/liveness` → 返回404（本地Python缺少路由）
- ❌ App无法连接到Backend（请求被路由到错误的服务）

### 为什么会返回404？

本地Python进程使用的是 `src.api.main:app`（备用入口点），它**缺少**：
- AI处理路由 (`/api/v1/ai/*`)
- 健康检查路由 (`/api/v1/health/*`)

正确的Docker容器使用 `src.main:app`（主入口点），包含所有路由。

## 解决方案

### 步骤1：停止冲突的Python进程

**方法A - 使用任务管理器（推荐）：**
1. 按 `Ctrl + Shift + Esc` 打开任务管理器
2. 切换到"详细信息"标签
3. 找到 PID 为 `29988` 的 `python.exe` 进程
4. 右键点击 → 结束任务

**方法B - 使用命令行：**
```powershell
# 在PowerShell中执行
Stop-Process -Id 29988 -Force
```

**方法C - 如果PID已经改变：**
```powershell
# 查找占用8000端口的进程
netstat -ano | findstr ":8000"

# 停止对应PID（替换<PID>为实际值）
Stop-Process -Id <PID> -Force
```

### 步骤2：验证问题解决

停止进程后，执行以下命令验证：

```bash
# 1. 检查端口监听状态（应该只有Docker）
netstat -ano | findstr ":8000"

# 2. 测试连接
curl http://192.168.13.222:8000/api/v1/health/liveness

# 应该返回：
# {"status":"alive","timestamp":"..."}
```

### 步骤3：测试App连接

1. 确保App配置的Backend URL为：`http://192.168.13.222:8000`
2. 在App中创建一个测试记录
3. 检查Backend日志：
   ```bash
   docker-compose logs backend --tail 50
   ```
   应该能看到POST请求到 `/api/v1/records/upload`

## 预防措施

为避免将来再次发生此问题：

1. **停止Docker容器前，不要手动启动Backend**
2. **如果需要本地开发，请使用不同的端口：**
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
   ```
3. **使用Docker开发时，始终通过docker-compose启动所有服务**

## 快速命令参考

```bash
# 启动所有服务
docker-compose up -d

# 查看Backend日志
docker-compose logs backend --follow

# 重启Backend
docker-compose restart backend

# 停止所有服务
docker-compose down

# 检查服务状态
docker-compose ps

# 检查端口占用
netstat -ano | findstr ":8000"
```

## 时间线

| 时间 | 事件 |
|------|------|
| 16:03:59 | Docker Backend最后一次成功处理请求(localhost) |
| 16:06:06 | PC发送请求到192.168.13.222:8000 → 404 |
| - | Backend日志中没有对应记录 → 确认请求未到达Docker |
| - | 发现PID 29988的python.exe占用8000端口 |
| - | 诊断：端口冲突导致请求路由错误 |

---

**执行完步骤1后，请运行步骤2验证问题是否解决。**
