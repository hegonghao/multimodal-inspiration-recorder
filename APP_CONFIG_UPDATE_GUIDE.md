# APP 配置更新指南

## 📅 更新日期
2025-11-07

## 🎯 更新内容

已将 APP 端的配置同步到后端 `.env` 文件中的配置：

### 更新的配置项：

| 配置项 | 旧值 | 新值 | 说明 |
|--------|------|------|------|
| `openai_base_url` | `http://localhost:11434/v1` | `https://cnapi.kksj.org/v1` | LLM API 地址 |
| `openai_model` | `llama3.1` | `gpt-4o-mini` | LLM 模型 |
| `deepgram_api_key` | `44e90ac460009a2a7cd9adfee1a65de28aba654b` | `823ee18611e5be6ce4a31f8a162ffd4f9a27845b` | 语音转文字 API Key |

---

## 📂 配置文件位置

### 1️⃣ **APP constants.dart**（硬编码配置）

**文件位置**: `app/lib/core/constants.dart`

**作用**:
- 定义 APP 的默认配置
- 作为 SharedPreferences 的 fallback
- 编译时确定，修改后需要重新编译

**关键配置**:
```dart
class ApiConstants {
  // APP 连接后端的地址（根据设备类型选择）
  static const String defaultBaseUrl = 'http://192.168.13.222:8000'; // 真机

  // 后端使用的 LLM 配置（仅供参考）
  static const String backendOpenAIBaseUrl = 'https://cnapi.kksj.org/v1';
  static const String backendOpenAIModel = 'gpt-4o-mini';
}
```

---

### 2️⃣ **APP Local Database**（运行时配置）

**文件位置**:
- Android: `/data/data/com.example.multimodal_inspiration_recorder/databases/inspiration_recorder.db`
- iOS: `APP Documents/inspiration_recorder.db`

**表**: `user_preferences`

**默认值定义**: `app/lib/data/database.dart:57-60`

```dart
class UserPreferences extends Table {
  TextColumn get openaiBaseUrl => text().withDefault(const Constant('https://cnapi.kksj.org/v1'))();
  TextColumn get openaiModel => text().withDefault(const Constant('gpt-4o-mini'))();
  TextColumn get deepgramApiKey => text().withDefault(const Constant('823ee18611e5be6ce4a31f8a162ffd4f9a27845b'))();
}
```

**数据库迁移**:
- Schema Version: `3` → `4`
- 迁移内容: 自动更新现有的 user_preferences 记录

---

### 3️⃣ **SharedPreferences**（持久化存储）

**位置**:
- Android: `/data/data/com.example.multimodal_inspiration_recorder/shared_prefs/FlutterSharedPreferences.xml`
- iOS: `~/Library/Preferences/com.example.multimodalInspirationRecorder.plist`

**存储的配置**:
```
key: api_base_url
value: (用户配置的后端 API 地址)
```

**特点**:
- ✅ 持久化存储，APP 重启不丢失
- ✅ 可通过 APP 设置页面修改（如果实现了）
- ⚠️ 默认为空，使用 constants.dart 的 fallback

---

## 🔄 配置更新流程

### 方式 1: 完全重新编译 APP（推荐）

这会应用所有的配置更改和数据库迁移：

```bash
# 1. 清理旧的构建文件
cd D:\multifuncinspirationrecord\app
flutter clean

# 2. 获取依赖
flutter pub get

# 3. 重新编译并运行
flutter run
```

**或者在 Android Studio 中**:
1. 点击 `Stop` 停止 APP
2. 点击 `File` → `Invalidate Caches / Restart...`
3. 选择 `Invalidate and Restart`
4. 重启后点击 `Run` 按钮

---

### 方式 2: 清除 APP 数据（完全重置）

如果遇到配置问题，可以清除 APP 所有数据：

#### Android 设备:
```bash
# 卸载 APP（这会清除所有数据）
adb uninstall com.example.multimodal_inspiration_recorder

# 重新安装
flutter run
```

#### 或者在 Android 设置中:
1. 打开 `设置` → `应用`
2. 找到 `灵感记录器`
3. 点击 `存储` → `清除数据`
4. 重新启动 APP

#### iOS 设备:
1. 长按 APP 图标
2. 选择 `删除 APP`
3. 重新运行: `flutter run`

---

### 方式 3: 只清除 SharedPreferences（保留记录）

如果只想重置配置，但保留记录数据：

**通过代码** (需要添加到设置页面):
```dart
import 'package:shared_preferences/shared_preferences.dart';

Future<void> resetSharedPreferences() async {
  final prefs = await SharedPreferences.getInstance();

  // 只清除 API 相关配置
  await prefs.remove('api_base_url');

  // 或清除所有 SharedPreferences
  // await prefs.clear();
}
```

---

## 🔍 验证配置是否生效

### 1. 检查 APP 使用的 API 地址

在 APP 日志中查看：
```
I/flutter: REQUEST[POST] => http://192.168.13.222:8000/api/v1/records/upload
                            ^^^^^^^^^^^^^^^^^^^^^^^^
                            这是 APP 使用的后端地址
```

### 2. 检查数据库配置

运行 APP 后，配置会自动迁移到 Version 4。

可以通过以下方式验证：
```dart
// 在 APP 中读取配置
final prefs = await database.getPreferences();
print('OpenAI Base URL: ${prefs?.openaiBaseUrl}');
print('OpenAI Model: ${prefs?.openaiModel}');
print('Deepgram API Key: ${prefs?.deepgramApiKey}');
```

### 3. 测试创建记录

1. 在 APP 中创建一条文字记录
2. 查看日志，确认 AI 处理成功
3. 检查记录是否有 `category_tags` 和 `summary`

---

## 📊 配置优先级

### APP 端优先级:

```
1. SharedPreferences 中的 api_base_url
   ↓ 如果不存在
2. constants.dart 中的 defaultBaseUrl
```

### APP 数据库配置优先级:

```
1. 用户通过设置页面修改的值（如果实现了）
   ↓ 如果不存在
2. 数据库迁移中更新的值
   ↓ 如果不存在
3. database.dart 中定义的默认值
```

---

## ⚠️ 注意事项

### 1. 后端 API 地址 vs LLM API 地址

**不要混淆这两个概念**:

- **后端 API 地址** (`defaultBaseUrl`):
  - APP 访问后端服务的地址
  - 例如: `http://192.168.13.222:8000`
  - 定义在: `constants.dart:22`

- **LLM API 地址** (`openaiBaseUrl`):
  - 后端调用 LLM 服务的地址
  - 例如: `https://cnapi.kksj.org/v1`
  - 定义在: `database.dart:57`
  - APP 只需要知道这个值（用于显示或配置），不会直接使用

### 2. 数据库 Schema 版本

当前版本: **4**

如果你修改了 `database.dart` 的表结构或默认值：
1. 增加 `schemaVersion`
2. 在 `onUpgrade` 中添加迁移逻辑
3. 运行 `dart run build_runner build --delete-conflicting-outputs`

### 3. Hot Reload vs Hot Restart

- **Hot Reload** (`r`): 不会更新 constants.dart 的值
- **Hot Restart** (`R`): 会重新加载所有代码，但不会重新创建数据库
- **完全重新运行**: 推荐使用 `flutter run`

### 4. 真机 vs 模拟器

根据你的设备类型，需要在 `constants.dart` 中选择正确的 `defaultBaseUrl`:

```dart
// Android 模拟器（10.0.2.2 指向宿主机 localhost）
// static const String defaultBaseUrl = 'http://10.0.2.2:8000';

// 真机（需要电脑和手机在同一 WiFi）
static const String defaultBaseUrl = 'http://192.168.13.222:8000';

// iOS 模拟器 / 桌面开发
// static const String defaultBaseUrl = 'http://localhost:8000';
```

---

## 🛠️ 常见问题排查

### 问题 1: 配置更新后仍显示旧值

**原因**: 使用了 Hot Reload
**解决**: 完全重新运行 APP: `flutter run`

### 问题 2: 数据库迁移没有执行

**原因**: APP 已有数据库，但 schema version 相同
**解决**:
1. 确认 `schemaVersion` 已增加
2. 卸载 APP 重新安装
3. 或在设备上清除 APP 数据

### 问题 3: SharedPreferences 中有旧配置

**原因**: 之前手动设置过 `api_base_url`
**解决**:
1. 清除 APP 数据
2. 或实现设置页面，允许用户修改

### 问题 4: APP 连接不到后端

**原因**:
- 真机和电脑不在同一 WiFi
- `defaultBaseUrl` 配置错误
- 后端服务未启动

**解决**:
1. 检查网络连接
2. 确认后端服务正在运行: `curl http://192.168.13.222:8000/api/v1/health`
3. 检查 APP 日志中的请求地址

---

## ✅ 验证清单

完成以下步骤，确保配置正确更新：

- [ ] 确认 `constants.dart` 中的 `defaultBaseUrl` 适合你的设备类型
- [ ] 确认 `database.dart` 的 `schemaVersion` 已增加到 4
- [ ] 运行 `dart run build_runner build` 生成新的数据库代码
- [ ] 完全重新编译 APP: `flutter clean && flutter run`
- [ ] 在 APP 中创建测试记录，验证 AI 功能正常
- [ ] 检查 APP 日志，确认使用正确的 API 地址
- [ ] （可选）在设置页面中验证配置值

---

## 📝 总结

### 已更新的文件:

1. ✅ `app/lib/core/constants.dart` - 添加了后端配置的参考
2. ✅ `app/lib/data/database.dart` - 更新了默认值和数据库迁移
3. ✅ `app/lib/data/database.g.dart` - 自动生成的数据库代码

### 需要执行的操作:

```bash
# 完全重新编译 APP
cd D:\multifuncinspirationrecord\app
flutter clean
flutter pub get
flutter run
```

### 配置生效后的行为:

- 新安装的 APP 会使用新的默认配置
- 已有 APP 会在首次启动时自动迁移数据库（Version 3→4）
- 所有 LLM 相关请求会使用新的 API 地址和模型

---

## 🔗 相关文件

- 后端配置: `.env`
- APP 配置: `app/lib/core/constants.dart`
- 数据库定义: `app/lib/data/database.dart`
- 存储服务: `app/lib/data/services/storage_service.dart`
