# Quickstart Guide: 多模输入灵感记录器

**Version**: 1.0.0
**Last Updated**: 2025-10-27
**Estimated Setup Time**: 30-45 minutes

## 目录

1. [系统要求](#系统要求)
2. [环境搭建](#环境搭建)
3. [后端设置](#后端设置-fastapi)
4. [前端设置](#前端设置-flutter)
5. [配置说明](#配置说明)
6. [运行应用](#运行应用)
7. [验证测试](#验证测试)
8. [常见问题](#常见问题)

---

## 系统要求

### 硬件要求

- **CPU**: 双核2.0GHz以上
- **RAM**: 至少4GB(推荐8GB)
- **存储**: 至少5GB可用空间
- **网络**: 稳定的互联网连接(初次设置)

### 软件要求

#### 后端开发

- **Python**: 3.11+
- **Redis**: 7.0+ (用于任务队列)
- **Git**: 版本控制

#### 前端开发

- **Flutter**: 3.16+
- **Dart**: 3.2+
- **Android Studio** / **Xcode**: 移动开发IDE

#### 可选依赖

- **Ollama**: 本地LLM服务(开发测试)
- **Docker**: 容器化部署
- **Notion账号**: 云端同步功能

---

## 环境搭建

### 1. 克隆项目仓库

```bash
git clone https://github.com/your-org/multimodal-recorder.git
cd multimodal-recorder
```

### 2. 安装系统依赖

#### Windows

```powershell
# 安装Chocolatey(如果未安装)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 安装Redis
choco install redis-64 -y

# 启动Redis服务
redis-server --service-install
redis-server --service-start
```

#### macOS

```bash
# 使用Homebrew安装
brew install redis python@3.11

# 启动Redis
brew services start redis
```

#### Linux (Ubuntu/Debian)

```bash
# 安装Python和Redis
sudo apt update
sudo apt install python3.11 python3.11-venv redis-server -y

# 启动Redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 3. 安装Ollama (本地LLM,可选)

**快速安装**:

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# 从 https://ollama.com/download 下载安装器
```

**拉取模型**:

```bash
ollama pull llama3.1
ollama serve  # 启动服务(http://localhost:11434)
```

---

## 后端设置 (FastAPI)

### 1. 创建Python虚拟环境

```bash
cd backend
python3.11 -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2. 安装Python依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**requirements.txt内容**:

```txt
# FastAPI核心
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Notion API
notion-client==2.3.0

# OpenAI
openai==1.6.1

# 异步任务队列
arq==0.25.0
redis==5.0.1

# 重试机制
tenacity==8.2.3

# 数据库
sqlalchemy[asyncio]==2.0.23
aiosqlite==0.19.0
alembic==1.13.1

# HTTP客户端
httpx==0.25.2

# 监控
prometheus-client==0.19.0
structlog==23.2.0

# 配置
python-dotenv==1.0.0

# 图像处理
pillow==10.1.0

# 测试
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
```

### 3. 创建环境变量文件

```bash
cp .env.example .env
```

**编辑 `.env`**:

```bash
# Application
APP_NAME=多模输入灵感记录器
ENVIRONMENT=development
DEBUG=true

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256

# LLM Configuration
OPENAI_API_KEY=sk-your-key-or-leave-empty-for-ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3.1

# Redis
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/app.db

# Notion (可选)
NOTION_TOKEN=
NOTION_DATABASE_ID=

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# Cost Control
MAX_DAILY_TOKENS=100000
COST_PER_TOKEN=0.000002

# Server
API_HOST=0.0.0.0
API_PORT=8000
WORKERS=4

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 4. 初始化数据库

```bash
# 创建数据目录
mkdir -p data

# 运行数据库迁移
alembic upgrade head

# 或手动初始化(如果未使用Alembic)
python -c "from app.database import init_db; init_db()"
```

### 5. 启动后端服务

```bash
# 启动FastAPI应用
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 在新终端启动ARQ Worker
arq app.worker.WorkerSettings
```

**验证后端**:

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 查看API文档
open http://localhost:8000/docs
```

---

## 前端设置 (Flutter)

### 1. 安装Flutter

**检查Flutter是否已安装**:

```bash
flutter --version
```

**如果未安装**,参考官方指南:
- Windows: https://docs.flutter.dev/get-started/install/windows
- macOS: https://docs.flutter.dev/get-started/install/macos
- Linux: https://docs.flutter.dev/get-started/install/linux

### 2. 检查Flutter环境

```bash
flutter doctor
```

**确保以下项目正常**:
- ✓ Flutter SDK
- ✓ Android toolchain (Android Studio)
- ✓ Xcode (仅macOS,用于iOS开发)
- ✓ Connected device (或模拟器)

### 3. 安装项目依赖

```bash
cd app
flutter pub get
```

### 4. 生成Drift数据库代码

```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

### 5. 配置API端点

**编辑 `lib/core/constants.dart`**:

```dart
class ApiConstants {
  // 开发环境
  static const String baseUrl = 'http://localhost:8000/api/v1';

  // Android模拟器使用
  // static const String baseUrl = 'http://10.0.2.2:8000/api/v1';

  // 真机测试使用(替换为你的电脑IP)
  // static const String baseUrl = 'http://192.168.1.100:8000/api/v1';

  // 生产环境
  // static const String baseUrl = 'https://api.inspiration-recorder.com/v1';
}
```

### 6. 运行Flutter应用

```bash
# 列出可用设备
flutter devices

# 运行到指定设备
flutter run

# 或指定设备ID
flutter run -d <device_id>

# iOS模拟器
flutter run -d iPhone

# Android模拟器
flutter run -d emulator-5554
```

---

## 配置说明

### Notion集成设置

**1. 创建Notion Integration**:

- 访问 https://www.notion.so/my-integrations
- 点击 "+ New integration"
- 填写基本信息:
  - Name: 多模输入灵感记录器
  - Associated workspace: 选择你的工作空间
  - Capabilities: 勾选 "Read content", "Update content", "Insert content"
- 点击 "Submit"
- 复制 "Internal Integration Token"

**2. 创建Notion数据库**:

- 在Notion中创建新的Database
- 添加以下属性:
  - 标题 (Title)
  - 分类 (Select)
  - 摘要 (Text)
  - 输入方式 (Select): voice/text/image
  - 创建时间 (Created time)
- 点击右上角 "..." → "Add connections" → 选择你的Integration
- 复制Database ID(从URL中获取):
  ```
  https://notion.so/your-workspace/DATABASE_ID?v=...
  ```

**3. 在应用中配置**:

- 打开应用 → 设置
- 填入 Notion Token 和 Database ID
- 点击 "测试连接" 验证

### LLM服务配置

#### 选项1: Ollama (本地,免费)

```bash
# 启动Ollama
ollama serve

# 在应用设置中:
# Base URL: http://localhost:11434/v1
# Model: llama3.1
# API Key: (留空)
```

#### 选项2: OpenAI (云端,付费)

```bash
# 在应用设置中:
# Base URL: https://api.openai.com/v1
# Model: gpt-3.5-turbo
# API Key: sk-your-openai-key
```

#### 选项3: 自托管vLLM

```bash
# 启动vLLM服务
python -m vllm.entrypoints.openai.api_server \
    --model microsoft/phi-2 \
    --host 0.0.0.0 \
    --port 8001

# 在应用设置中:
# Base URL: http://localhost:8001/v1
# Model: microsoft/phi-2
# API Key: (留空)
```

---

## 运行应用

### 开发模式

**终端1 - 后端API**:
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**终端2 - ARQ Worker**:
```bash
cd backend
source venv/bin/activate
arq app.worker.WorkerSettings
```

**终端3 - Flutter应用**:
```bash
cd app
flutter run
```

**可选 - Ollama**:
```bash
ollama serve
```

### Docker Compose (推荐)

```bash
# 构建并启动所有服务
docker-compose up --build

# 后台运行
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

**docker-compose.yml示例**:

```yaml
version: '3.8'

services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - OPENAI_BASE_URL=http://ollama:11434/v1
    depends_on:
      - redis
      - ollama
    volumes:
      - ./backend/data:/app/data

  worker:
    build: ./backend
    command: arq app.worker.WorkerSettings
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  redis_data:
  ollama_data:
```

---

## 验证测试

### 1. 后端API测试

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 创建测试记录
curl -X POST http://localhost:8000/api/v1/records \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试灵感",
    "content": "这是一条测试灵感记录,用于验证系统功能是否正常运行。",
    "input_type": "text"
  }'

# 获取记录列表
curl http://localhost:8000/api/v1/records

# AI分类测试
curl -X POST http://localhost:8000/api/v1/ai/classify \
  -H "Content-Type: application/json" \
  -d '{"content": "我想开发一个AI产品"}'
```

### 2. Flutter应用测试

**手动测试清单**:

- [ ] 应用启动成功
- [ ] 主界面显示正常
- [ ] 语音录制功能正常
- [ ] 文字输入功能正常
- [ ] 图片上传和OCR识别正常
- [ ] AI分类和摘要自动生成
- [ ] 记录列表显示
- [ ] 同步状态指示器
- [ ] 设置页面可访问
- [ ] Notion连接测试通过(如已配置)

### 3. 集成测试

```bash
# 后端集成测试
cd backend
pytest tests/integration/ -v

# Flutter集成测试
cd app
flutter test integration_test/
```

---

## 常见问题

### Q1: Redis连接失败

**错误**: `ConnectionRefusedError: [Errno 111] Connection refused`

**解决方案**:
```bash
# 检查Redis是否运行
redis-cli ping
# 应返回 PONG

# 如果未运行,启动Redis
# Windows
redis-server

# macOS/Linux
sudo systemctl start redis
```

### Q2: Flutter build_runner失败

**错误**: `Conflicting outputs for file`

**解决方案**:
```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

### Q3: Ollama模型下载慢

**解决方案**:
```bash
# 使用国内镜像
export OLLAMA_MODELS_DIR=/path/to/models
ollama pull llama3.1

# 或使用已下载的模型文件
ollama create my-model -f Modelfile
```

### Q4: Android模拟器无法连接后端

**问题**: `Failed to connect to http://localhost:8000`

**解决方案**:

Android模拟器需使用特殊IP:
```dart
// lib/core/constants.dart
static const String baseUrl = 'http://10.0.2.2:8000/api/v1';
```

或使用电脑实际IP(在同一局域网):
```dart
static const String baseUrl = 'http://192.168.1.100:8000/api/v1';
```

### Q5: iOS录音权限被拒绝

**解决方案**:

在 `ios/Runner/Info.plist` 中添加:
```xml
<key>NSMicrophoneUsageDescription</key>
<string>需要访问麦克风以录制语音灵感</string>
<key>NSSpeechRecognitionUsageDescription</key>
<string>需要语音识别功能以转写录音内容</string>
```

### Q6: OCR识别准确率低

**解决方案**:

1. **提高图片质量**:
   - 确保光线充足
   - 避免模糊和倾斜
   - 使用高分辨率(≥640x480)

2. **启用图像预处理**:
   ```dart
   // 在设置中启用
   Settings.enableImagePreprocessing = true;
   ```

3. **检查ML Kit模型是否已下载**:
   - 首次使用需要联网下载模型(~18MB)

### Q7: Notion同步失败

**错误**: `APIResponseError: object_not_found`

**排查步骤**:

1. **验证Integration连接**:
   - 确保Database已共享给Integration
   - 在Notion Database页面 → "..." → "Add connections"

2. **检查Database ID**:
   ```
   正确格式: 32位十六进制字符串
   示例: a1b2c3d4e5f67890a1b2c3d4e5f67890
   ```

3. **测试API连接**:
   ```bash
   curl https://api.notion.com/v1/databases/YOUR_DATABASE_ID \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Notion-Version: 2022-06-28"
   ```

### Q8: 数据库迁移错误

**错误**: `alembic.util.exc.CommandError: Can't locate revision`

**解决方案**:
```bash
# 删除迁移历史
rm -rf alembic/versions/*.py

# 重新生成迁移
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

---

## 下一步

### 学习资源

- **API文档**: http://localhost:8000/docs
- **数据模型**: 查看 `specs/1-multimodal-capture/data-model.md`
- **技术调研**: 查看 `specs/1-multimodal-capture/research.md`

### 开发指南

- **添加新功能**: 参考 `CONTRIBUTING.md`
- **测试指南**: 参考 `tests/README.md`
- **部署指南**: 参考 `DEPLOYMENT.md`

### 获取帮助

- **GitHub Issues**: https://github.com/your-org/multimodal-recorder/issues
- **Discord社区**: https://discord.gg/your-server
- **Email支持**: support@example.com

---

## 故障排除清单

遇到问题时,按以下顺序检查:

1. **基础环境**:
   - [ ] Python 3.11+ 已安装
   - [ ] Flutter 3.16+ 已安装
   - [ ] Redis 正在运行
   - [ ] 网络连接正常

2. **依赖安装**:
   - [ ] `pip install -r requirements.txt` 成功
   - [ ] `flutter pub get` 成功
   - [ ] `flutter pub run build_runner build` 成功

3. **配置文件**:
   - [ ] `.env` 文件已创建并填写
   - [ ] API端点配置正确
   - [ ] Notion Token和Database ID正确(如使用)

4. **服务运行**:
   - [ ] FastAPI运行在 http://localhost:8000
   - [ ] ARQ Worker已启动
   - [ ] Ollama运行在 http://localhost:11434 (如使用)

5. **日志检查**:
   - 后端日志: `tail -f backend/logs/app.log`
   - Flutter日志: 查看IDE控制台
   - Redis日志: `redis-cli monitor`

---

**祝您开发顺利! 🚀**

如有任何问题,请参考上述故障排除部分或联系技术支持。