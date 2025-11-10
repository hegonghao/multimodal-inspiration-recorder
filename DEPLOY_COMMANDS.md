# 服务器部署命令列表

如果自动脚本 `deploy_fix.sh` 无法执行，按照以下步骤手动执行命令。

## 前置条件

```bash
# 进入项目目录
cd ~/multimodal-inspiration-recorder

# 拉取最新代码
git pull origin main
```

---

## 部署步骤

### 1. 验证 .env 文件

```bash
# 检查文件存在
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

---

### 2. 验证 docker-compose.yml 配置

```bash
# 检查 env_file 配置是否存在
cat docker-compose.yml | grep -B 5 -A 2 "env_file"
```

**预期输出**（应该看到两处）：
```yaml
  backend:
    ...
    env_file:
      - .env

  worker:
    ...
    env_file:
      - .env
```

---

### 3. 测试环境变量加载

```bash
# 测试变量是否被正确替换（不会启动容器）
docker-compose config | grep -E "OPENAI_API_KEY|OPENAI_MODEL" | head -4
```

**正确输出示例**：
```yaml
- OPENAI_API_KEY=sk-AUwTbAHEb85Lty150eDaC6335e464bCf99CaF5C0Fa00C98f
- OPENAI_MODEL=gpt-4o-mini
```

**错误输出示例**（需要修复）：
```yaml
- OPENAI_API_KEY=
- OPENAI_MODEL=
```

如果看到空值，可能的原因：
- .env 文件不在项目根目录
- .env 文件权限问题：`chmod 644 .env`
- .env 文件格式问题（Windows 换行符）：`dos2unix .env`（需要安装 dos2unix）

---

### 4. 停止现有容器

```bash
docker-compose down
```

**预期输出**：
```
Stopping inspiration-recorder-backend ... done
Stopping inspiration-recorder-worker ... done
Stopping inspiration-recorder-redis ... done
Removing containers...
```

---

### 5. 重新构建容器（可选，如果有代码变更）

```bash
# 如果后端代码有更新，需要重新构建
docker-compose build backend worker
```

如果只是配置变更（如 docker-compose.yml），可以跳过此步骤。

---

### 6. 启动服务

```bash
docker-compose up -d backend worker redis
```

**预期输出**：
```
Creating inspiration-recorder-redis ... done
Creating inspiration-recorder-backend ... done
Creating inspiration-recorder-worker ... done
```

---

### 7. 验证容器内环境变量

```bash
# 检查 backend 容器的环境变量（不显示完整值）
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

**完整值检查**（确认 model 不为空）：
```bash
docker exec inspiration-recorder-backend env | grep "OPENAI_MODEL="
```

**预期输出**：
```
OPENAI_MODEL=gpt-4o-mini
```

**不应该是**：
```
OPENAI_MODEL=
```

---

### 8. 检查启动日志

```bash
# 查看最近30行日志
docker-compose logs backend | tail -30
```

**查找关键日志**：
```bash
docker-compose logs backend | grep -E "AI Processor|LLM|WARN"
```

**✅ 正确的日志示例**：
```json
{"event": "Using LLM config from .env"}
{"event": "AI Processor initialized: provider=LLMProvider.OPENAI, model=gpt-4o-mini"}
```

**❌ 错误的日志示例**（需要进一步排查）：
```
WARN[0000] The "OPENAI_API_KEY" variable is not set
{"event": "AI Processor initialized: provider=LLMProvider.OPENAI, model="}
```

如果仍然看到错误：
1. 返回步骤 3，确认 `docker-compose config` 输出正确
2. 检查 .env 文件位置和格式
3. 查看完整日志：`docker-compose logs backend > backend.log`

---

### 9. 清理数据库配置（如果 AI 处理仍然失败）

即使环境变量正确，如果数据库中有旧的错误配置，后端会优先使用数据库值。

#### 9.1 检查数据库当前配置

```bash
docker exec inspiration-recorder-backend sqlite3 /app/data/inspirations.db \
  "SELECT openai_base_url, openai_model, openai_api_key FROM user_preferences WHERE id = 1;"
```

**如果输出类似以下（非空值）**：
```
https://cnapi.kksj.org/v1|gpt-4o-mini|sk-xxx
```

则需要清理数据库配置。

**如果输出为空**：
```
||
```

则数据库配置正确，跳过清理步骤。

#### 9.2 执行清理脚本

```bash
# 复制清理脚本到容器
docker cp clear_db_config.py inspiration-recorder-backend:/app/

# 执行清理
docker exec inspiration-recorder-backend python /app/clear_db_config.py
```

**预期输出**：
```
🧹 Clearing API configurations from database...
✅ Configurations cleared!

📊 Verification:
  openai_base_url = ""
  openai_model = ""
  openai_api_key = None
  deepgram_api_key = ""

✅ All values are empty - backend will use .env defaults
```

#### 9.3 重启服务

```bash
docker-compose restart backend worker
```

#### 9.4 再次检查日志

```bash
docker-compose logs backend | tail -20 | grep "AI Processor"
```

应该看到：
```json
{"event": "Using LLM config from .env"}
{"event": "AI Processor initialized: provider=LLMProvider.OPENAI, model=gpt-4o-mini"}
```

---

## 功能测试

### 测试 1: 在手机 App 上录制语音

1. 打开手机 App
2. 录制一段 10-30 秒的语音
3. 等待上传和处理（约 10-30 秒）
4. 检查是否自动生成了：
   - 标题
   - 分类标签

### 测试 2: 实时监控后端日志

在另一个终端窗口运行：

```bash
docker-compose logs -f backend | grep -E "transcription|LLM|title|category"
```

**正常处理流程日志示例**：
```json
{"event": "Processing voice input", "file_size": 245678}
{"event": "Transcription started"}
{"event": "Transcription completed", "language": "zh", "confidence": 0.92}
{"event": "Calling LLM API for metadata generation"}
{"event": "LLM API call succeeded", "model": "gpt-4o-mini", "tokens": 156}
{"event": "Generated title", "title": "关于项目优化的想法"}
{"event": "Generated categories", "categories": ["工作", "技术"]}
{"event": "Metadata updated successfully"}
{"event": "AI processing completed"}
```

**失败日志示例**（需要排查）：
```json
{"event": "Transcription completed", "language": "zh", "confidence": 0.92}
{"event": "Calling LLM API for metadata generation"}
{"event": "LLM API call failed (attempt 1/3): Connection error."}
{"event": "LLM API call failed (attempt 2/3): Connection error."}
{"event": "LLM API call failed (attempt 3/3): Connection error."}
{"event": "AI processing failed: APIConnectionError: Connection error."}
```

---

## 故障排查

### 问题：环境变量仍然为空

**诊断命令**：
```bash
# 1. 确认当前目录
pwd

# 2. 确认 .env 存在
ls -la .env

# 3. 查看 .env 内容（前 30 行）
head -30 .env

# 4. 检查文件权限
ls -l .env

# 5. 检查文件格式（是否有 BOM 或 Windows 换行符）
file .env
```

**可能的解决方案**：

1. **文件权限问题**：
   ```bash
   chmod 644 .env
   ```

2. **文件格式问题**：
   ```bash
   # 安装 dos2unix（如果需要）
   # Ubuntu/Debian: apt-get install dos2unix
   # CentOS/RHEL: yum install dos2unix

   dos2unix .env
   ```

3. **文件不存在或位置错误**：
   ```bash
   # 确保在项目根目录
   cd ~/multimodal-inspiration-recorder

   # 如果文件丢失，从 backend/.env 复制或重新创建
   cp backend/.env .env
   ```

---

### 问题：LLM API 连接失败

**诊断步骤**：

1. **确认环境变量已加载**：
   ```bash
   docker exec inspiration-recorder-backend env | grep OPENAI
   ```

2. **测试 API 连接**：
   ```bash
   docker exec inspiration-recorder-backend python -c "
   import requests
   url = 'https://cnapi.kksj.org/v1/models'
   headers = {'Authorization': 'Bearer sk-AUwTbAHEb85Lty150eDaC6335e464bCf99CaF5C0Fa00C98f'}
   try:
       resp = requests.get(url, headers=headers, timeout=10)
       print(f'Status: {resp.status_code}')
       print(f'Response: {resp.text[:200]}')
   except Exception as e:
       print(f'Error: {e}')
   "
   ```

3. **检查配置读取逻辑**：
   ```bash
   docker exec inspiration-recorder-backend python -c "
   from src.config import settings
   print(f'Base URL: {settings.OPENAI_BASE_URL}')
   print(f'Model: {settings.OPENAI_MODEL}')
   print(f'API Key (first 10 chars): {settings.OPENAI_API_KEY[:10]}...')
   "
   ```

---

### 问题：Docker Compose 版本不兼容

**检查版本**：
```bash
docker-compose --version
```

**建议版本**：
- Docker Compose v2.0.0 或更高
- 如果版本过低，升级：
  ```bash
  # 方法 1: 使用 docker compose (v2)
  docker compose --version

  # 方法 2: 升级 docker-compose
  sudo pip install --upgrade docker-compose
  ```

---

## 完整部署检查清单

复制以下清单，逐项检查：

```
[ ] git pull 完成
[ ] .env 文件存在于根目录
[ ] .env 文件包含所有必需变量 (OPENAI_*, DEEPGRAM_*, PADDLEOCR_*)
[ ] docker-compose.yml 包含 env_file: .env 配置
[ ] docker-compose config 显示正确的变量值（非空）
[ ] docker-compose down 完成
[ ] docker-compose up -d 完成
[ ] docker exec ... env 显示正确的环境变量
[ ] 启动日志无 WARN 警告
[ ] AI Processor 日志显示 model=gpt-4o-mini（非空）
[ ] 数据库 API 配置字段为空（或已清理）
[ ] 手机 App 测试：语音录制后自动生成标题和分类
[ ] 后端日志：LLM API 调用成功，无 Connection error
```

---

## 相关文档

- **DOCKER_ENV_FIX.md** - Docker 环境变量问题详细诊断和修复指南
- **FIX_LLM_API_CONNECTION.md** - LLM API 连接失败根本原因分析
- **clear_db_config.py** - 数据库配置清理脚本
- **test_llm_connection.py** - LLM API 连接测试工具
- **SERVER_DEPLOYMENT_GUIDE.md** - 完整服务器部署文档

---

## 获取帮助

如果以上步骤仍无法解决问题：

1. **收集完整日志**：
   ```bash
   docker-compose logs backend > backend.log 2>&1
   docker-compose logs worker > worker.log 2>&1
   docker-compose config > compose-config.yml 2>&1
   ```

2. **脱敏处理**（删除 API 密钥）：
   ```bash
   sed -i 's/sk-[A-Za-z0-9]*/sk-***REDACTED***/g' backend.log
   sed -i 's/sk-[A-Za-z0-9]*/sk-***REDACTED***/g' compose-config.yml
   ```

3. **GitHub 提 Issue**：
   - 附上 `compose-config.yml`
   - 附上 `backend.log` 和 `worker.log`（最后 200 行）
   - 说明操作系统、Docker 版本、Docker Compose 版本
   - 描述操作步骤和预期/实际结果

**GitHub Issues**: https://github.com/hegonghao/multimodal-inspiration-recorder/issues
