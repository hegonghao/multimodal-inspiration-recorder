# Docker 环境变量加载问题修复

## 🔴 问题现象

服务器启动后出现环境变量未设置的警告：

```
WARN[0000] The "OPENAI_API_KEY" variable is not set. Defaulting to a blank string.
WARN[0000] The "OPENAI_BASE_URL" variable is not set. Defaulting to a blank string.
WARN[0000] The "OPENAI_MODEL" variable is not set. Defaulting to a blank string.
```

后端日志显示：
```json
{"event": "AI Processor initialized: provider=LLMProvider.OPENAI, model="}
```

**model 字段为空**，导致所有 LLM API 调用失败。

---

## 🎯 根本原因

**docker-compose.yml 缺少 `env_file` 配置**

Docker Compose 的环境变量加载机制：

1. **隐式自动读取**（不可靠）：
   - Docker Compose 可能自动读取项目根目录的 `.env` 文件
   - 但这个行为在不同版本和环境下不一致
   - 依赖工作目录和 Compose 版本

2. **显式 env_file 配置**（推荐）：
   ```yaml
   services:
     backend:
       env_file:
         - .env  # ✅ 明确指定环境变量文件
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY}
   ```

### 当前配置问题

```yaml
# docker-compose.yml (修复前)
services:
  backend:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}  # ❌ 变量未定义，默认为空
      - OPENAI_BASE_URL=${OPENAI_BASE_URL}
      - OPENAI_MODEL=${OPENAI_MODEL}
```

没有 `env_file` 配置，Docker Compose 无法找到变量定义来源。

---

## 🛠️ 修复方案

### 1. 修复 docker-compose.yml（已完成）

为 `backend` 和 `worker` 服务添加 `env_file` 配置：

```yaml
services:
  backend:
    env_file:
      - .env  # ✅ 显式指定环境变量文件
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      # ... 其他环境变量

  worker:
    env_file:
      - .env  # ✅ 同样配置
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      # ... 其他环境变量
```

### 2. 服务器部署步骤

#### 步骤 1: 更新代码

```bash
cd ~/multimodal-inspiration-recorder
git pull origin main
```

#### 步骤 2: 验证 .env 文件存在

```bash
# 检查根目录 .env 文件
ls -la .env

# 查看关键配置（不显示完整密钥）
cat .env | grep -E "OPENAI_|DEEPGRAM_|PADDLEOCR_" | sed 's/=.*/=***/'
```

**预期输出**：
```
OPENAI_API_KEY=***
OPENAI_BASE_URL=***
OPENAI_MODEL=***
DEEPGRAM_API_KEY=***
PADDLEOCR_API_URL=***
PADDLEOCR_TOKEN=***
```

#### 步骤 3: 验证 docker-compose.yml 配置

```bash
# 检查 env_file 配置
cat docker-compose.yml | grep -A 3 "env_file:"
```

**预期输出**：
```yaml
    env_file:
      - .env
```

#### 步骤 4: 测试环境变量加载

```bash
# 测试变量替换（不会启动容器）
docker-compose config | grep -A 5 "OPENAI"
```

**预期输出**（应该显示实际值，不是空字符串）：
```yaml
- OPENAI_API_KEY=sk-AUwTbAHEb85Lty150eDaC6335e464bCf99CaF5C0Fa00C98f
- OPENAI_BASE_URL=https://cnapi.kksj.org/v1
- OPENAI_MODEL=gpt-4o-mini
```

如果看到空值，检查：
- .env 文件是否存在于项目根目录
- .env 文件权限是否正确（chmod 644 .env）
- .env 文件格式是否正确（无 BOM，Unix 换行符）

#### 步骤 5: 重新构建和启动服务

```bash
# 停止现有容器
docker-compose down

# 重新构建（如有代码更改）
docker-compose build backend worker

# 启动服务
docker-compose up -d backend worker redis
```

#### 步骤 6: 验证环境变量已加载

```bash
# 检查后端容器环境变量（不显示完整值）
docker exec inspiration-recorder-backend env | grep -E "OPENAI_|DEEPGRAM_|PADDLEOCR_" | sed 's/=.*/=***/'
```

**预期输出**：
```
OPENAI_API_KEY=***
OPENAI_BASE_URL=***
OPENAI_MODEL=***
DEEPGRAM_API_KEY=***
PADDLEOCR_API_URL=***
PADDLEOCR_TOKEN=***
```

#### 步骤 7: 检查启动日志

```bash
# 查看后端初始化日志
docker-compose logs backend | grep -E "AI Processor|LLM"
```

**预期输出（修复后）**：
```json
{"event": "Using LLM config from .env"}
{"event": "AI Processor initialized: provider=LLMProvider.OPENAI, model=gpt-4o-mini"}
```

**不应该再出现**：
```
❌ WARN: The "OPENAI_API_KEY" variable is not set
❌ {"event": "AI Processor initialized: provider=LLMProvider.OPENAI, model="}
```

---

## 🧪 功能测试

### 测试 1: 使用手机 App 录制语音

1. 在手机 App 上录制一段语音（10-30秒）
2. 等待上传和处理完成
3. 检查是否自动生成了标题和分类

### 测试 2: 查看后端日志

```bash
docker-compose logs -f backend | grep -E "transcription|LLM|title|category"
```

**预期日志流程**：
```json
{"event": "Transcription completed", "language": "zh", "confidence": 0.92}
{"event": "Calling LLM API for metadata generation"}
{"event": "LLM API call succeeded", "model": "gpt-4o-mini"}
{"event": "Generated title", "title": "关于XXX的想法"}
{"event": "Generated categories", "categories": ["工作", "创意"]}
{"event": "Metadata updated successfully"}
```

**不应该看到**：
```json
❌ {"event": "LLM API call failed (attempt 3/3): Connection error."}
❌ {"event": "AI processing failed: APIConnectionError: Connection error."}
```

---

## 🔍 故障排查

### 问题 1: 仍然提示环境变量未设置

**检查项**：
```bash
# 1. 确认 .env 文件在根目录
pwd
ls -la .env

# 2. 确认 .env 文件内容正确
cat .env | head -30

# 3. 确认 docker-compose.yml 已更新
git log --oneline -5

# 4. 确认使用了最新版本
docker-compose config | grep env_file -A 2
```

**可能原因**：
- .env 文件不在项目根目录
- git pull 后未重启服务
- .env 文件格式问题（Windows 换行符、BOM）

**解决方法**：
```bash
# 转换换行符（如果需要）
dos2unix .env

# 或者手动重新创建
cat > .env << 'EOF'
OPENAI_API_KEY=sk-AUwTbAHEb85Lty150eDaC6335e464bCf99CaF5C0Fa00C98f
OPENAI_BASE_URL=https://cnapi.kksj.org/v1
OPENAI_MODEL=gpt-4o-mini
# ... 其他配置
EOF
```

### 问题 2: LLM API 调用仍然失败

**检查项**：
```bash
# 1. 确认环境变量已加载到容器
docker exec inspiration-recorder-backend env | grep OPENAI

# 2. 确认 API Key 有效
docker exec inspiration-recorder-backend python -c "
from src.config import settings
print(f'Base URL: {settings.OPENAI_BASE_URL}')
print(f'Model: {settings.OPENAI_MODEL}')
print(f'API Key: {settings.OPENAI_API_KEY[:10]}...')
"

# 3. 测试 API 连接
docker exec inspiration-recorder-backend python test_llm_connection.py
```

### 问题 3: 数据库仍有旧配置

即使修复了环境变量，如果数据库中仍有旧的错误配置，后端会优先使用数据库配置。

**检查数据库**：
```bash
docker exec inspiration-recorder-backend sqlite3 /app/data/inspirations.db \
  "SELECT openai_base_url, openai_model, openai_api_key FROM user_preferences WHERE id = 1;"
```

**如果输出非空值，需要清理**：
```bash
# 复制清理脚本到容器
docker cp clear_db_config.py inspiration-recorder-backend:/app/

# 执行清理
docker exec inspiration-recorder-backend python clear_db_config.py

# 重启服务
docker-compose restart backend worker
```

---

## 📋 完整部署检查清单

- [ ] **代码更新**: `git pull` 完成
- [ ] **.env 文件**: 存在于根目录，包含所有必需变量
- [ ] **docker-compose.yml**: 包含 `env_file: .env` 配置
- [ ] **环境变量测试**: `docker-compose config` 显示正确值
- [ ] **容器重启**: `docker-compose up -d` 完成
- [ ] **容器环境变量**: `docker exec ... env` 显示正确值
- [ ] **启动日志**: 无 WARN 警告，model 字段非空
- [ ] **数据库配置**: API 配置字段为空（使用 .env 默认值）
- [ ] **LLM API 测试**: `test_llm_connection.py` 通过
- [ ] **功能测试**: 手机录音后自动生成标题和分类

---

## 🔗 相关文档

- `FIX_LLM_API_CONNECTION.md` - LLM API 连接失败修复指南
- `clear_db_config.py` - 数据库配置清理脚本
- `test_llm_connection.py` - LLM API 连接测试工具
- `SERVER_DEPLOYMENT_GUIDE.md` - 完整服务器部署文档

---

## 📞 技术支持

如果按照以上步骤仍未解决：

1. **收集诊断信息**：
   ```bash
   # 环境信息
   docker --version
   docker-compose --version
   pwd

   # 配置验证
   docker-compose config > compose-config.yml

   # 容器日志
   docker-compose logs backend > backend.log
   docker-compose logs worker > worker.log
   ```

2. **在 GitHub 提 Issue**：
   - 附上 `compose-config.yml`（脱敏后）
   - 附上 `backend.log` 和 `worker.log`
   - 说明操作步骤和预期/实际结果

**GitHub Issues**: https://github.com/hegonghao/multimodal-inspiration-recorder/issues
