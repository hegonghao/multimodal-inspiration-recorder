# Notion 同步配置指南

## 问题诊断

您当前遇到的问题：**点击同步显示"没有待同步记录"**

### 根本原因

1. ✅ **后端已修复**：同步服务现在从用户偏好数据库读取 Notion 凭据
2. ✅ **Flutter 代码已修复**：设置页面现在会将凭据同步到后端 API
3. ✅ **Gradle 构建问题已修复**：Flutter 应用现在可以正常构建
4. ⚠️ **待解决**：后端数据库中仍是测试占位符，不是真实凭据
5. ⚠️ **待解决**：所有同步任务处于 FAILED 状态，需要重置

### 当前状态

```bash
# 后端数据库中的凭据（占位符）
notion_token: secret_test_token_placeholder_for_demonstration_purposes_only
notion_database_id: test_database_id_1234567890abcdef

# 同步状态
总记录数: 7
已同步: 0
待同步: 0 (已重置为 7)
失败: 0 (已清空)
```

## 解决方案

### 方法 1：使用 Python 测试脚本（推荐）

1. **编辑测试脚本**：
   ```bash
   # 打开 test_notion_sync.py
   # 填入您的真实 Notion 凭据
   NOTION_TOKEN = "secret_xxxxx..."  # 您的真实 token
   NOTION_DATABASE_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # 您的真实 database ID
   ```

2. **运行脚本**：
   ```bash
   python test_notion_sync.py
   ```

   脚本会自动：
   - ✅ 测试 Notion 连接
   - ✅ 更新凭据到后端
   - ✅ 重置失败的同步任务
   - ✅ 触发同步

### 方法 2：在 Flutter 应用中配置

1. **重新启动 Flutter 应用**（如果还没启动）：
   ```bash
   cd app
   flutter run
   ```

2. **在应用中配置凭据**：
   - 打开设置页面
   - 填入您的真实 Notion Integration Token
   - 填入您的真实 Notion Database ID
   - 点击"保存设置"按钮
   - **重要**：这次保存会将凭据同步到后端！

3. **重试失败的同步任务**：
   ```bash
   curl -X POST "http://localhost:8000/api/v1/sync/retry-failed"
   ```

4. **触发同步**：
   - 在应用中点击"立即同步"按钮

### 方法 3：直接使用 curl 命令

```bash
# 1. 更新凭据
curl -X PUT "http://localhost:8000/api/v1/preferences" \
  -H "Content-Type: application/json" \
  -d '{
    "notion_token": "secret_your_actual_token_here",
    "notion_database_id": "your_actual_database_id_here"
  }'

# 2. 测试连接
curl -X POST "http://localhost:8000/api/v1/preferences/test-notion" \
  -H "Content-Type: application/json" \
  -d '{
    "notion_token": "secret_your_actual_token_here",
    "notion_database_id": "your_actual_database_id_here"
  }'

# 3. 重试失败的同步
curl -X POST "http://localhost:8000/api/v1/sync/retry-failed"

# 4. 触发同步
curl -X POST "http://localhost:8000/api/v1/sync/trigger"
```

## 获取 Notion 凭据

### 1. 创建 Notion Integration

1. 访问：https://www.notion.so/my-integrations
2. 点击 "New integration"
3. 填写名称（如："灵感记录器"）
4. 选择关联的 workspace
5. 点击 "Submit"
6. **复制 "Internal Integration Token"**（以 `secret_` 开头）

### 2. 获取 Database ID

1. 在 Notion 中打开您的数据库页面
2. 点击右上角 "..." 菜单 → "Copy link"
3. 链接格式：`https://www.notion.so/workspace/database_id?v=...`
4. **Database ID** 是链接中的 32 位字符串（带连字符）

### 3. 连接 Integration 到数据库

1. 在 Notion 数据库页面
2. 点击右上角 "..." 菜单
3. 选择 "Connections" → "Connect to"
4. 找到并选择您创建的 Integration
5. 点击 "Confirm"

## 验证同步

### 检查同步状态

```bash
curl http://localhost:8000/api/v1/sync/status | python -m json.tool
```

期望看到：
```json
{
  "total_records": 7,
  "synced_count": 0,
  "pending_count": 7,
  "failed_count": 0,
  "sync_enabled": true  // ✅ 应该是 true
}
```

### 查看同步队列

```bash
curl http://localhost:8000/api/v1/sync/queue?limit=10 | python -m json.tool
```

期望看到任务状态从 `status: 3` (FAILED) 变为 `status: 0` (PENDING)

### 监控后端日志

```bash
docker-compose logs -f backend
```

观察同步过程中的日志输出

## 常见问题

### Q1: 为什么点击同步显示"没有待同步记录"？

**A**: 因为所有同步任务都处于 FAILED 状态，`trigger_sync` 只查找 PENDING 状态的任务。

**解决方案**：运行 `curl -X POST "http://localhost:8000/api/v1/sync/retry-failed"` 将失败任务重置为 PENDING

### Q2: 为什么 sync_enabled 是 false？

**A**: 后端检查用户偏好数据库，发现 `notion_token` 或 `notion_database_id` 为空或是测试占位符。

**解决方案**：在 Flutter 应用或使用 API 更新真实的 Notion 凭据

### Q3: Flutter 应用保存设置后，后端仍然是旧数据？

**A**: 可能是 Gradle 构建失败，新代码没有运行。

**解决方案**：
1. 确保 `flutter run` 成功启动
2. 检查控制台没有构建错误
3. 重新保存设置

### Q4: 同步任务一直失败？

**A**: 可能的原因：
- Notion Integration Token 无效
- Database ID 错误
- Integration 未连接到数据库
- 网络问题

**解决方案**：
1. 使用 `/preferences/test-notion` 端点测试连接
2. 检查 Notion Integration 权限
3. 确认 Database 已连接 Integration

## 技术细节

### 修复内容

1. **后端同步服务** (`backend/src/services/sync_service.py`):
   ```python
   # 现在从用户偏好读取配置
   prefs_result = await self.db.execute(
       select(UserPreferences).where(UserPreferences.id == 1)
   )
   prefs = prefs_result.scalar_one_or_none()

   notion_sync_enabled = (
       prefs is not None and
       prefs.notion_token is not None and
       prefs.notion_token.strip() != "" and
       prefs.notion_database_id is not None and
       prefs.notion_database_id.strip() != ""
   )
   ```

2. **Flutter 设置页面** (`app/lib/presentation/pages/settings_page.dart`):
   ```dart
   // 保存到本地数据库后，同步到后端 API
   await apiService.updatePreferences(updateData);
   ```

3. **Gradle 配置** (`app/android/build.gradle.kts`):
   ```kotlin
   // 合并重复的 subprojects 块，移除 evaluationDependsOn
   subprojects {
       afterEvaluate {
           // 编译配置
       }
   }
   ```

### 同步流程

```
用户配置 Notion 凭据
    ↓
Flutter 保存到本地数据库
    ↓
Flutter 同步到后端 API (/api/v1/preferences)
    ↓
后端保存到数据库 (user_preferences 表)
    ↓
用户点击"立即同步"
    ↓
Flutter 调用 /api/v1/sync/trigger
    ↓
后端检查用户偏好，发现凭据已配置
    ↓
后端查找 PENDING 状态的同步任务
    ↓
后端将任务加入 ARQ 队列
    ↓
ARQ Worker 执行同步到 Notion
```

## 下一步

完成配置后，您可以：

1. **测试文本输入同步**：
   - 在应用中创建新的文本记录
   - 观察是否自动创建同步任务
   - 检查 Notion 数据库是否出现新记录

2. **测试自动同步**：
   - 等待自动同步间隔（默认 30 分钟）
   - 或修改 `sync_interval` 为更短时间测试

3. **测试网络自动同步**：
   - 在离线状态创建记录
   - 恢复网络连接
   - 观察是否自动触发同步

---

**需要帮助？**
- 查看后端日志：`docker-compose logs -f backend`
- 查看 Flutter 日志：`flutter logs`
- 检查同步状态：`curl http://localhost:8000/api/v1/sync/status`
