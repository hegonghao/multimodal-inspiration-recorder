# 修复 LLM API 连接失败问题

## 🔴 问题诊断

从服务器日志可以看到:
```json
{"event": "LLM API call failed (attempt 3/3): Connection error."}
{"event": "AI processing failed: APIConnectionError: Connection error."}
```

## 🎯 根本原因

**App 数据库中的硬编码默认值覆盖了服务器 `.env` 的正确配置**

### 问题流程:

1. App 数据库默认值: `openaiBaseUrl = 'https://cnapi.kksj.org/v1'`
2. 用户在手机设置页面保存配置时,这个默认值被同步到后端数据库
3. 后端 `AIProcessor` 优先从数据库读取配置,而不是 `.env`
4. 结果: 使用了无法访问的 API 地址

```python
# backend/src/services/ai_processor.py
if prefs and prefs.openai_api_key:
    base_url = prefs.openai_base_url  # ❌ 从数据库读取错误配置
else:
    base_url = settings.OPENAI_BASE_URL  # ✅ 应该从 .env 读取
```

---

## 🛠️ 修复步骤

### 步骤 1: 清理服务器数据库配置

在服务器上执行:

```bash
# 进入项目目录
cd /path/to/multimodal-inspiration-recorder

# 运行清理脚本
docker exec -it inspiration-recorder-backend python clear_app_api_configs.py
```

这个脚本会:
- ✅ 清空数据库中的 `openai_base_url`, `openai_model`, `deepgram_api_key`
- ✅ 让后端回退使用 `.env` 配置
- ✅ 显示当前和更新后的配置对比

### 步骤 2: 重启服务

```bash
docker-compose restart backend worker
```

### 步骤 3: 验证修复

查看日志,确认使用正确的配置:

```bash
docker-compose logs -f backend | grep -i "llm"
```

应该看到:
```
✅ Using LLM config from .env
✅ AI Processor initialized: base_url=https://正确的地址
```

而不是:
```
❌ Loaded LLM config from user preferences
❌ Connection error to https://cnapi.kksj.org/v1
```

### 步骤 4: 测试 AI 功能

在手机 App 上:
1. 录制一段语音
2. 检查是否自动生成标题和分类
3. 查看服务器日志,确认没有 "Connection error"

---

## 🔧 代码修复(已完成)

### 1. App 数据库 - 移除硬编码默认值

**修改文件**: `app/lib/data/database.dart`

```dart
// 之前 (❌ 错误):
TextColumn get openaiBaseUrl => text().withDefault(const Constant('https://cnapi.kksj.org/v1'))();
TextColumn get openaiModel => text().withDefault(const Constant('gpt-4o-mini'))();

// 之后 (✅ 正确):
TextColumn get openaiBaseUrl => text().withDefault(const Constant(''))();
TextColumn get openaiModel => text().withDefault(const Constant(''))();
```

### 2. 数据库迁移 - 清空错误配置

**修改文件**: `app/lib/data/database.dart`

```dart
// Version 4 -> 5: Clear hardcoded API configs
if (from < 5) {
  await customStatement('''
    UPDATE user_preferences
    SET openai_base_url = '',
        openai_api_key = NULL,
        openai_model = '',
        deepgram_api_key = ''
    WHERE id = 1
  ''');
}
```

### 3. Schema 版本升级

```dart
@override
int get schemaVersion => 5;  // 4 -> 5
```

### 4. 保存逻辑 - 添加注释

**修改文件**: `app/lib/presentation/pages/settings_page.dart`

```dart
// NOTE: LLM and STT configs are managed by backend .env
// Mobile app should NOT override these unless explicitly provided
final openaiBaseUrl = _openaiBaseUrlController.text.trim();
if (openaiBaseUrl.isNotEmpty) {
  updateData['openai_base_url'] = openaiBaseUrl;
}
```

---

## 📝 配置管理原则

### ✅ 推荐做法:

**服务器端 (`.env`)**: 管理所有 API 密钥和端点
```bash
# backend/.env
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=your_openrouter_key
OPENAI_MODEL=openai/gpt-4o-mini

DEEPGRAM_API_KEY=your_deepgram_key
PADDLEOCR_TOKEN=your_paddleocr_token
```

**手机端 (数据库)**: 只管理用户个性化设置
```
✅ Backend URL (服务器地址)
✅ Notion Token (个人 Notion 集成)
✅ Notion Database ID
✅ 同步间隔、自动分类等 UI 偏好
```

### ❌ 避免做法:

- ❌ 在 App 数据库硬编码 LLM API 配置
- ❌ 让手机用户配置 API 密钥 (安全风险)
- ❌ App 配置覆盖服务器配置

---

## 🚀 后续优化建议

### 1. 隐藏不需要的设置字段

在手机设置页面,可以考虑隐藏 LLM/STT 配置:

```dart
// 注释掉或条件隐藏
// _buildAISection(),  // 普通用户不需要配置
```

### 2. 添加"高级设置"分区

```dart
// 只在开发模式或高级模式显示
if (kDebugMode || _preferences.advancedMode) {
  _buildAdvancedSection(),  // LLM, Deepgram 配置
}
```

### 3. 添加配置测试功能

在设置页面添加"测试连接"按钮:

```dart
ElevatedButton(
  onPressed: () async {
    final result = await apiService.testLLMConnection(...);
    // 显示测试结果
  },
  child: Text('测试 LLM 连接'),
)
```

---

## 🔍 故障排查

### 如果修复后仍然失败:

#### 1. 检查 `.env` 配置

```bash
# 在服务器上
cat backend/.env | grep -E 'OPENAI|DEEPGRAM'
```

确保:
- ✅ `OPENAI_BASE_URL` 指向可访问的端点
- ✅ `OPENAI_API_KEY` 有效
- ✅ `OPENAI_MODEL` 模型可用

#### 2. 测试 API 连接

```bash
# 在服务器上测试 LLM API
docker exec -it inspiration-recorder-backend python test_llm_connection.py
```

#### 3. 检查数据库配置

```bash
# 进入容器
docker exec -it inspiration-recorder-backend bash

# 查询数据库
sqlite3 /app/data/inspirations.db "SELECT openai_base_url, openai_model FROM user_preferences;"
```

应该看到空值:
```
||   # 表示都是空的,会使用 .env 默认值
```

#### 4. 查看初始化日志

```bash
docker-compose logs backend | grep "AI Processor"
```

应该看到:
```
✅ Using LLM config from .env
✅ AI Processor initialized: provider=custom, model=gpt-4o-mini
```

---

## 📚 相关文档

- `test_llm_connection.py` - LLM API 连接诊断工具
- `clear_app_api_configs.py` - 清理数据库配置脚本
- `backend/DEPLOYMENT.md` - 服务器部署指南
- `SERVER_DEPLOYMENT_GUIDE.md` - 完整部署文档

---

## 💬 联系支持

如果问题仍未解决:
1. 运行 `test_llm_connection.py` 获取详细诊断
2. 查看完整的后端日志: `docker-compose logs backend > backend.log`
3. 在 GitHub 提 Issue 并附上日志

**GitHub**: https://github.com/hegonghao/multimodal-inspiration-recorder/issues
