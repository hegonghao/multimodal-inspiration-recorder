# 多模输入灵感记录器 - FastAPI 后端

[![Python 3.11](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个基于 FastAPI 的现代化后端服务，专为多模输入灵感记录器设计，集成了 OpenAI 兼容的 LLM API、实时语音转写、图片处理等功能。

## 🚀 核心特性

### LLM 服务集成
- **多提供商支持**: OpenAI、Azure OpenAI、以及自定义兼容接口
- **智能故障转移**: 自动切换到备用 LLM 提供商
- **请求缓存**: 智能缓存相同请求的响应
- **流式响应**: 支持实时流式对话体验
- **成本控制**: 实时监控和限制使用成本

### 安全管理
- **JWT 认证**: 基于令牌的用户认证系统
- **API 密钥管理**: 为不同应用场景生成独立 API 密钥
- **速率限制**: 多层次的请求频率控制
- **密码安全**: 强密码策略和安全哈希存储

### 性能优化
- **异步处理**: 全异步架构，支持高并发
- **连接池**: HTTP 和 Redis 连接池管理
- **智能缓存**: Redis 和内存双重缓存策略
- **指标监控**: Prometheus 集成的完整监控体系

### 语音处理
- **实时转写**: 支持实时语音转文字
- **格式支持**: 多种音频格式兼容
- **缓存优化**: 相同音频的智能缓存

## 📋 系统要求

- **Python**: 3.11+
- **Redis**: 6.0+ (用于缓存和速率限制)
- **内存**: 最低 512MB，推荐 2GB+
- **存储**: 最低 1GB 可用空间

## 🛠️ 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd 多模输入灵感记录器

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入必要配置
nano .env
```

**关键配置项**:
```env
# 安全配置
SECRET_KEY=your-super-secret-key-change-this

# LLM API 配置
OPENAI_API_KEY=your-openai-api-key

# Redis 配置
REDIS_URL=redis://localhost:6379
```

### 3. 启动 Redis

```bash
# 使用 Docker 启动 Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 或本地安装启动
redis-server
```

### 4. 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用内置脚本
python -m app.main
```

### 5. 验证服务

```bash
# 检查服务状态
curl http://localhost:8000/health

# 查看 API 文档
open http://localhost:8000/docs
```

## 🐳 Docker 部署

### 完整服务部署

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
```

### 单独后端服务

```bash
# 构建镜像
docker build -t multimodal-backend .

# 运行容器
docker run -d \
  --name backend \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e SECRET_KEY=your-secret \
  multimodal-backend
```

## 📚 API 使用指南

### 认证

所有 API 请求都需要认证，支持两种方式：

#### 1. JWT 令牌认证

```bash
# 用户登录获取令牌
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# 使用令牌访问 API
curl -X POST http://localhost:8000/api/v1/llm/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'
```

#### 2. API 密钥认证

```bash
# 使用 API 密钥
curl -X POST http://localhost:8000/api/v1/llm/chat \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'
```

### 核心接口

#### LLM 聊天完成

```bash
# 普通对话
curl -X POST http://localhost:8000/api/v1/llm/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Explain quantum computing"}
    ],
    "model": "gpt-3.5-turbo",
    "max_tokens": 500,
    "temperature": 0.7
  }'
```

#### 流式对话

```bash
# 流式响应 (Server-Sent Events)
curl -X POST http://localhost:8000/api/v1/llm/chat/stream \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Tell me a story"}
    ]
  }'
```

#### 语音转写

```bash
# 上传音频文件进行转写
curl -X POST http://localhost:8000/api/v1/llm/transcribe \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: audio/mpeg" \
  --data-binary @audio_file.mp3
```

#### 使用统计

```bash
# 获取使用统计
curl -X GET http://localhost:8000/api/v1/llm/usage \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔧 高级配置

### LLM 提供商配置

支持多个 LLM 提供商的配置和故障转移：

```python
# 在 app/services/llm_service.py 中配置
from app.models.llm import LLMProviderConfig, LLMProvider

configs = [
    LLMProviderConfig(
        provider=LLMProvider.OPENAI,
        api_key="your-openai-key",
        base_url="https://api.openai.com/v1",
        model="gpt-4"
    ),
    LLMProviderConfig(
        provider=LLMProvider.AZURE_OPENAI,
        api_key="your-azure-key",
        base_url="https://your-resource.openai.azure.com",
        model="gpt-4"
    )
]
```

### 缓存策略配置

```python
# Redis 缓存配置
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-password

# 缓存 TTL 设置
LLM_CACHE_TTL=3600  # 1小时
TRANSCRIPTION_CACHE_TTL=86400  # 24小时
```

### 速率限制配置

```python
# 在 app/services/rate_limiter.py 中配置规则
RateLimitRule(
    name="premium_user_llm",
    limit=1000,
    window=3600,  # 每小时1000次
    type=RateLimitType.USER_BASED
)
```

## 📊 监控和日志

### Prometheus 指标

服务自动暴露以下指标：

- `http_requests_total`: HTTP 请求总数
- `llm_requests_total`: LLM 请求总数
- `llm_tokens_total`: Token 使用总数
- `cache_hits_total`: 缓存命中数
- `error_rate`: 错误率

### 日志结构

采用结构化 JSON 日志格式：

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "event": "request_completed",
  "method": "POST",
  "path": "/api/v1/llm/chat",
  "status_code": 200,
  "duration": 1.234,
  "user_id": "user_123"
}
```

### Sentry 集成

配置 Sentry 进行错误监控：

```env
SENTRY_DSN=your-sentry-dsn
```

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_llm_service.py

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

### 测试环境

```bash
# 启动测试环境
docker-compose -f docker-compose.test.yml up -d

# 运行集成测试
pytest tests/integration/
```

## 🔒 安全最佳实践

### 1. 生产环境配置

```env
# 关闭调试模式
DEBUG=false
ENVIRONMENT=production

# 使用强密钥
SECRET_KEY=your-very-strong-secret-key-min-32-chars

# 限制 CORS 来源
ALLOWED_ORIGINS=https://yourdomain.com
```

### 2. API 密钥管理

- 定期轮换 API 密钥
- 使用最小权限原则
- 监控 API 密钥使用情况

### 3. 网络安全

- 使用 HTTPS (TLS 1.3)
- 配置防火墙规则
- 启用请求速率限制

## 🚀 性能优化

### 1. 缓存优化

- 合理设置缓存 TTL
- 使用 Redis 集群提高可用性
- 实施缓存预热策略

### 2. 数据库优化

- 使用连接池
- 实施读写分离
- 定期清理过期数据

### 3. 并发优化

- 调整 worker 进程数
- 使用异步 I/O
- 实施请求队列

## 📈 扩展性

### 水平扩展

```bash
# 使用 Kubernetes 进行扩展
kubectl scale deployment backend --replicas=5

# 使用负载均衡器
kubectl expose deployment backend --type=LoadBalancer
```

### 微服务拆分

- LLM 服务独立部署
- 认证服务独立
- 缓存服务独立

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 开发规范

- 遵循 PEP 8 代码风格
- 编写单元测试
- 更新文档
- 通过 CI 检查

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 故障排除

### 常见问题

#### 1. Redis 连接失败

```bash
# 检查 Redis 是否运行
redis-cli ping

# 检查网络连接
telnet localhost 6379
```

#### 2. LLM API 错误

```bash
# 检查 API 密钥
curl -H "Authorization: Bearer YOUR_KEY" https://api.openai.com/v1/models

# 检查网络连接
curl -I https://api.openai.com
```

#### 3. 内存使用过高

```bash
# 检查内存使用
docker stats

# 调整 worker 数量
uvicorn app.main:app --workers 2
```

### 日志分析

```bash
# 查看错误日志
docker-compose logs backend | grep ERROR

# 查看访问日志
docker-compose logs backend | grep "request_completed"
```

## 📞 支持

- 📧 Email: support@multimodal-recorder.com
- 📖 文档: [https://docs.multimodal-recorder.com](https://docs.multimodal-recorder.com)
- 🐛 问题反馈: [GitHub Issues](https://github.com/your-repo/issues)

---

**注意**: 这是一个企业级后端服务，请确保在生产环境中遵循安全最佳实践。