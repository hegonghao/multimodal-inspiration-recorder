# App Backend URL 配置指南

## 问题

之前App的Backend URL是硬编码在代码中（`http://192.168.13.222:8000`），无法在App中修改。

## 解决方案

✅ 已在**设置页面**添加了Backend URL配置选项！

## 如何配置Backend URL

### 步骤1：重新编译并安装App

由于代码修改，需要重新编译App：

```bash
cd app
flutter run
```

或者如果需要生成APK：
```bash
flutter build apk
```

### 步骤2：打开App设置

1. 启动App
2. 点击底部导航的"设置"按钮
3. 滚动到顶部，你会看到新的**"Backend 服务器"**配置区域

### 步骤3：配置Backend URL

在"Backend URL"输入框中输入你的Backend服务器地址：

**真机（手机和电脑在同一WiFi）：**
```
http://192.168.13.222:8000
```

**Android模拟器：**
```
http://10.0.2.2:8000
```

**iOS模拟器或桌面开发：**
```
http://localhost:8000
```

### 步骤4：保存并重启App

1. 点击页面底部的"保存设置"按钮
2. **完全关闭App**（从后台清除）
3. **重新打开App**
4. Backend URL配置生效！

## 配置界面说明

```
┌──────────────────────────────────┐
│ Backend 服务器                    │
│ 配置后端服务器地址（重启App后生效） │
│                                  │
│ Backend URL                      │
│ [http://192.168.13.222:8000]    │
│ 手机和电脑需在同一WiFi网络         │
│                                  │
│ ⚠️ 修改后需要重启App才能生效。    │
│    确保地址格式正确：http://IP:端口│
└──────────────────────────────────┘
```

## 重要提示

⚠️ **修改Backend URL后必须重启App**
- Backend URL在App启动时初始化ApiService
- 修改后不会立即生效
- 必须完全关闭并重新打开App

✅ **地址格式要求**
- 必须以 `http://` 或 `https://` 开头
- 包含IP地址或域名
- 包含端口号（如 `:8000`）
- 示例：`http://192.168.13.222:8000`

✅ **网络要求**
- 真机：手机和电脑必须在**同一WiFi网络**
- 模拟器：使用特殊地址（Android用10.0.2.2，iOS用localhost）

## 验证配置是否成功

### 方法1：创建测试记录

1. 重启App后，尝试创建一条文本记录
2. 如果显示"记录已保存"且能看到AI分类和摘要，说明连接成功

### 方法2：查看Backend日志

```bash
docker-compose logs backend --follow
```

创建记录时应该看到：
```
POST /api/v1/records/upload HTTP/1.1" 201 Created
```

### 方法3：检查数据库

```bash
docker exec inspiration-recorder-backend python -c "
import asyncio
from sqlalchemy import select, func
from src.database import get_db
from src.models.inspiration import InspirationRecord

async def check():
    db_gen = get_db()
    db = await anext(db_gen)
    try:
        result = await db.execute(select(func.count()).select_from(InspirationRecord))
        count = result.scalar()
        print(f'Total records: {count}')
    finally:
        await db_gen.aclose()

asyncio.run(check())
"
```

## 常见问题

### Q: 修改后还是连接不上？
A:
1. 确认已经**完全关闭并重启App**
2. 检查手机和电脑是否在**同一WiFi网络**
3. 检查Backend URL格式是否正确
4. 在PC上测试URL：`curl http://192.168.13.222:8000/api/v1/health/liveness`

### Q: 如何找到电脑的IP地址？
A:
**Windows:**
```powershell
ipconfig | findstr "IPv4"
```

**macOS/Linux:**
```bash
ifconfig | grep "inet "
```

### Q: 重启App后还是用旧地址？
A:
1. 确认设置已保存成功（显示"设置已保存"提示）
2. 彻底关闭App（从后台任务中清除）
3. 重新打开App

### Q: 能不能不重启App就生效？
A:
目前不支持。Backend URL在App启动时初始化，要让修改生效需要重启App。
如果经常需要切换环境，建议在代码中配置多个预设选项。

## 代码改动说明

### 添加的文件修改

**settings_page.dart:**
- 添加 `_backendUrlController` 控制器
- 添加 `_buildBackendSection()` 配置区域
- 在 `_loadPreferences()` 中从StorageService加载Backend URL
- 在 `_savePreferences()` 中保存Backend URL到StorageService

**main.dart (已有逻辑):**
```dart
baseUrl: storageService.getString(
  StorageService.keyApiBaseUrl
) ?? ApiConstants.defaultBaseUrl
```

### 存储位置

Backend URL保存在：
- **存储服务**: SharedPreferences
- **键名**: `api_base_url`
- **默认值**: `ApiConstants.defaultBaseUrl` (http://192.168.13.222:8000)

## 下一步

1. **重新编译App**: `cd app && flutter run`
2. **打开设置**: App → 设置 → Backend 服务器
3. **输入URL**: http://192.168.13.222:8000
4. **保存设置**: 点击"保存设置"按钮
5. **重启App**: 完全关闭并重新打开
6. **测试连接**: 创建一条测试记录

---

**Backend已修复并正常运行，现在App也有了配置界面。你可以随时修改Backend URL了！**
