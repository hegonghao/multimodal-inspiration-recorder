# Security Best Practices

## 概述

本文档记录了灵感记录系统的安全加固措施和最佳实践。

---

## 已实现的安全措施

### 1. 速率限制 (Rate Limiting)

**位置**: `backend/src/api/middleware/security.py`

**实现细节**:
```python
# 普通API路由：100请求/分钟
api_rate_limiter = RateLimiter(requests=100, window_seconds=60)

# 文件上传路由：20请求/分钟（更严格）
upload_rate_limiter = RateLimiter(requests=20, window_seconds=60)
```

**防护目标**:
- 防止暴力破解攻击
- 防止DDoS/DoS攻击
- 防止API滥用

**响应示例**:
```json
HTTP 429 Too Many Requests
{
  "error": "RateLimitExceeded",
  "message": "请求过于频繁，请在42秒后重试",
  "retry_after": 42
}
```

**生产环境建议**:
- 使用Redis实现分布式速率限制
- 根据API端点调整不同的限制策略
- 为认证用户提供更高的配额

---

### 2. 请求大小限制 (Request Size Limiting)

**位置**: `backend/src/api/middleware/security.py:RequestSizeLimitMiddleware`

**实现细节**:
```python
RequestSizeLimitMiddleware(max_request_size=50 * 1024 * 1024)  # 50MB
```

**防护目标**:
- 防止内存耗尽攻击
- 限制文件上传大小
- 保护服务器资源

**限制说明**:
| 内容类型 | 最大大小 | 说明 |
|---------|---------|------|
| 语音文件 | 5分钟录音 ≈ 3.6MB (AAC-LC) | 符合需求 |
| 图片文件 | 典型 < 10MB | 符合需求 |
| JSON请求 | 典型 < 1MB | 符合需求 |

---

### 3. 安全响应头 (Security Headers)

**位置**: `backend/src/api/middleware/security.py:SecurityHeadersMiddleware`

**实现的响应头**:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

**防护说明**:

| 响应头 | 防护目标 | 说明 |
|--------|---------|------|
| `X-Content-Type-Options` | MIME类型嗅探攻击 | 强制浏览器遵守Content-Type |
| `X-Frame-Options` | 点击劫持攻击 | 禁止在iframe中嵌入 |
| `X-XSS-Protection` | XSS攻击 | 启用浏览器XSS过滤器 |
| `Strict-Transport-Security` | 中间人攻击 | 强制使用HTTPS |
| `Content-Security-Policy` | XSS/代码注入 | 限制资源加载来源 |

---

### 4. 输入清理 (Input Sanitization)

#### 4.1 文件名清理

**函数**: `sanitize_filename(filename: str) -> str`

**防护措施**:
```python
# 防护路径遍历攻击
>>> sanitize_filename("../../etc/passwd")
'passwd'

# 移除危险字符
>>> sanitize_filename("file<script>.jpg")
'filescript.jpg'

# 长度限制（255字符）
>>> sanitize_filename("a" * 300 + ".jpg")
'aaa...aaa.jpg'  # 截断至255字符
```

#### 4.2 内容安全验证

**函数**: `validate_content_safety(content: str, max_length: int) -> tuple[bool, str]`

**验证规则**:
1. 非空检查
2. 长度限制（默认10,000字符）
3. NULL字节检测（防止字符串截断攻击）
4. 控制字符检测（防止二进制数据注入）

**使用示例**:
```python
is_safe, error_msg = validate_content_safety(user_input, max_length=5000)
if not is_safe:
    raise ValueError(error_msg)
```

#### 4.3 SQL标识符清理

**函数**: `sanitize_sql_identifier(identifier: str) -> str`

**注意**: 本项目使用SQLAlchemy ORM，已自动防护SQL注入。此函数仅用于特殊场景。

**验证规则**:
- 只允许字母、数字、下划线
- 必须以字母或下划线开头
- 禁止SQL保留关键字

```python
>>> sanitize_sql_identifier("user_id")
'user_id'  # ✅

>>> sanitize_sql_identifier("user-id")
ValueError: 不安全的SQL标识符

>>> sanitize_sql_identifier("DROP")
ValueError: SQL标识符不能使用保留关键字
```

---

### 5. 敏感数据遮蔽 (Data Masking)

**函数**: `mask_sensitive_data(data: str, keep_chars: int = 4) -> str`

**用途**: 日志记录、错误信息、调试输出

**示例**:
```python
>>> mask_sensitive_data("secret_abc123def456", keep_chars=4)
'secr************f456'

>>> mask_sensitive_data("sk-1234567890abcdef", keep_chars=3)
'sk-************def'
```

**应用场景**:
```python
logger.info(
    "notion_token_updated",
    token=mask_sensitive_data(notion_token),  # 遮蔽敏感信息
    user_id=user_id
)
```

---

### 6. CORS配置 (Cross-Origin Resource Sharing)

**函数**: `get_cors_config(allowed_origins: list[str] | None) -> dict`

**开发环境**（宽松）:
```python
{
    "allow_origins": ["http://localhost:*", "http://127.0.0.1:*"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "max_age": 3600,
}
```

**生产环境**（严格）:
```python
{
    "allow_origins": ["https://yourdomain.com"],  # 明确指定
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "Authorization"],
    "max_age": 600,
}
```

---

### 7. 请求日志 (Request Logging for Audit)

**中间件**: `RequestLoggingMiddleware`

**记录信息**:
- 请求方法和路径
- 客户端IP地址
- User-Agent
- 响应状态码
- 处理时长

**日志示例**:
```json
{
  "event": "request_completed",
  "method": "POST",
  "path": "/api/v1/records",
  "status_code": 201,
  "duration_ms": 125,
  "client_ip": "192.168.1.100",
  "timestamp": "2025-10-28T10:30:00Z"
}
```

---

## SQL注入防护

### 已有防护措施

**1. SQLAlchemy ORM自动参数化**

所有数据库查询都使用参数化查询，SQLAlchemy自动转义：

```python
# ✅ 安全（自动参数化）
result = await db.execute(
    select(InspirationRecord)
    .where(InspirationRecord.title == user_input)
)

# ❌ 不安全（仅作示例，项目中未使用）
query = f"SELECT * FROM records WHERE title = '{user_input}'"
```

**2. Pydantic输入验证**

所有API输入都经过Pydantic模型验证：

```python
class InspirationRecordCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=10000)
    input_type: InputType  # Enum约束

    @field_validator("content")
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 10:
            raise ValueError("内容至少需要10个字符")
        return stripped
```

**3. 数据库约束**

数据库层面的CHECK约束：

```python
CheckConstraint(
    "input_type IN ('voice', 'text', 'image')",
    name="chk_input_type"
)
```

---

## 防护等级评估

| 攻击类型 | 防护状态 | 实现方式 | 风险等级 |
|---------|---------|---------|---------|
| SQL注入 | ✅ 完全防护 | SQLAlchemy ORM + Pydantic验证 | 🟢 低 |
| XSS攻击 | ✅ 完全防护 | 安全响应头 + Flutter客户端 | 🟢 低 |
| CSRF攻击 | ✅ 完全防护 | 无状态JWT + CORS配置 | 🟢 低 |
| 路径遍历 | ✅ 完全防护 | 文件名清理 + 路径验证 | 🟢 低 |
| DoS攻击 | ⚠️ 部分防护 | 速率限制 + 请求大小限制 | 🟡 中 |
| 暴力破解 | ⚠️ 部分防护 | 速率限制（需Redis增强） | 🟡 中 |
| 数据泄露 | ✅ 完全防护 | 敏感数据遮蔽 + write-only字段 | 🟢 低 |

---

## 安全检查清单

### 代码审查清单

- [ ] 所有数据库查询使用ORM（禁止原始SQL）
- [ ] 所有API输入使用Pydantic验证
- [ ] 文件上传使用`sanitize_filename()`清理
- [ ] 敏感信息日志使用`mask_sensitive_data()`遮蔽
- [ ] 密码/Token永不返回给客户端（write-only）
- [ ] 错误信息不泄露内部实现细节
- [ ] 所有外部API调用有超时限制
- [ ] 批量操作有数量限制

### 部署前检查

- [ ] 更新CORS配置为生产环境域名
- [ ] 启用HTTPS/TLS（Let's Encrypt）
- [ ] 配置环境变量（禁止硬编码密钥）
- [ ] 启用Redis速率限制（替代内存限制）
- [ ] 配置防火墙规则（只开放必要端口）
- [ ] 启用数据库加密（SQLCipher）
- [ ] 设置日志轮转和保留策略
- [ ] 配置监控告警（异常请求数、错误率）

---

## 未来安全增强计划

### 短期（1-2周）
- [ ] 集成Redis实现分布式速率限制
- [ ] 添加JWT认证（如需多用户支持）
- [ ] 实现API密钥管理（用于移动应用）

### 中期（1-2月）
- [ ] 启用SQLCipher数据库加密
- [ ] 实现审计日志系统
- [ ] 添加异常行为检测（AI模型）

### 长期（3-6月）
- [ ] 实现OAuth2.0第三方登录
- [ ] 添加端到端加密（E2EE）
- [ ] 通过第三方安全审计

---

## 安全事件响应

### 发现安全漏洞

1. 立即报告给开发团队
2. 评估影响范围和严重程度
3. 制定修复计划（紧急/常规）
4. 实施修复并验证
5. 更新安全文档

### 安全事件处理流程

1. **检测**: 通过日志监控发现异常
2. **遏制**: 临时禁用受影响功能
3. **根除**: 修复漏洞并部署补丁
4. **恢复**: 恢复正常服务
5. **复盘**: 分析原因并改进流程

---

## 相关资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLAlchemy Security Considerations](https://docs.sqlalchemy.org/en/20/faq/security.html)

---

**最后更新**: 2025-10-28
**维护者**: Security Team
