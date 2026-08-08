"""
Security Middleware
安全中间件：速率限制、输入验证、安全响应头
"""

import time
from collections import defaultdict
from typing import Callable, Dict, Optional
from datetime import datetime, timedelta

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


# ==================== Rate Limiting ====================


class RateLimiter:
    """
    简单的内存速率限制器

    生产环境建议使用Redis实现分布式速率限制
    """

    def __init__(self, requests: int = 100, window_seconds: int = 60):
        """
        Args:
            requests: 时间窗口内允许的请求数
            window_seconds: 时间窗口大小（秒）
        """
        self.requests = requests
        self.window_seconds = window_seconds
        self.clients: Dict[str, list] = defaultdict(list)

    def is_allowed(self, client_id: str) -> tuple[bool, Optional[int]]:
        """
        检查客户端是否允许请求

        Args:
            client_id: 客户端标识（通常是IP地址）

        Returns:
            (是否允许, 重试等待秒数)
        """
        now = time.time()
        cutoff_time = now - self.window_seconds

        # 清理过期的请求记录
        self.clients[client_id] = [
            req_time for req_time in self.clients[client_id] if req_time > cutoff_time
        ]

        # 检查是否超过限制
        if len(self.clients[client_id]) >= self.requests:
            oldest_request = min(self.clients[client_id])
            retry_after = int(oldest_request + self.window_seconds - now) + 1
            return False, retry_after

        # 记录新请求
        self.clients[client_id].append(now)
        return True, None

    def cleanup_old_clients(self):
        """清理长时间未活动的客户端记录"""
        now = time.time()
        cutoff = now - (self.window_seconds * 10)  # 10倍时间窗口

        inactive_clients = [
            client_id
            for client_id, requests in self.clients.items()
            if all(req_time < cutoff for req_time in requests)
        ]

        for client_id in inactive_clients:
            del self.clients[client_id]


# 全局速率限制器实例
# API路由：100 req/min
api_rate_limiter = RateLimiter(requests=100, window_seconds=60)

# 文件上传路由：20 req/min（更严格）
upload_rate_limiter = RateLimiter(requests=20, window_seconds=60)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""

    async def dispatch(self, request: Request, call_next: Callable):
        # 跳过健康检查端点
        if (
            request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]
            or request.url.path.startswith("/api/v1/health")
        ):
            return await call_next(request)

        # 获取客户端标识（IP地址）
        client_ip = request.client.host if request.client else "unknown"

        # 根据路径选择不同的限制器
        if "/records" in request.url.path and request.method == "POST":
            # 文件上传使用更严格的限制
            allowed, retry_after = upload_rate_limiter.is_allowed(client_ip)
        else:
            # 普通API请求
            allowed, retry_after = api_rate_limiter.is_allowed(client_ip)

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                path=request.url.path,
                method=request.method,
                retry_after=retry_after,
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "RateLimitExceeded",
                    "message": f"请求过于频繁，请在{retry_after}秒后重试",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        return response


# ==================== Request Size Limiting ====================


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """请求大小限制中间件"""

    def __init__(
        self,
        app: ASGIApp,
        max_request_size: int = 50 * 1024 * 1024,  # 50MB default
    ):
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next: Callable):
        # 检查Content-Length头
        content_length = request.headers.get("content-length")

        if content_length:
            content_length = int(content_length)

            if content_length > self.max_request_size:
                logger.warning(
                    "request_size_exceeded",
                    client_ip=request.client.host if request.client else "unknown",
                    path=request.url.path,
                    content_length=content_length,
                    max_size=self.max_request_size,
                )

                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "error": "RequestTooLarge",
                        "message": f"请求体过大，最大允许{self.max_request_size // (1024*1024)}MB",
                        "max_size_mb": self.max_request_size // (1024 * 1024),
                    },
                )

        response = await call_next(request)
        return response


# ==================== Security Headers ====================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全响应头中间件"""

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # 添加安全响应头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # HSTS is only valid when the public endpoint is HTTPS. Set it at the
        # TLS-terminating proxy or enable it for the production API only.
        import os

        if os.getenv("ENVIRONMENT", "development") == "production":
            response.headers[
                "Strict-Transport-Security"
            ] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        # 移除可能泄露服务器信息的头
        # MutableHeaders doesn't have pop() method, use try/except with del instead
        try:
            del response.headers["Server"]
        except KeyError:
            pass  # Header doesn't exist, which is fine

        return response


# ==================== Input Sanitization ====================


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，防止路径遍历攻击

    Args:
        filename: 原始文件名

    Returns:
        清理后的安全文件名

    Example:
        >>> sanitize_filename("../../etc/passwd")
        'passwd'
        >>> sanitize_filename("file<script>.jpg")
        'filescript.jpg'
    """
    import re
    from pathlib import Path

    # 只保留文件名部分，移除路径
    filename = Path(filename).name

    # 移除危险字符
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", filename)

    # 限制长度
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[: 255 - len(ext) - 1] + "." + ext if ext else name[:255]

    # 如果清理后为空，使用默认名称
    if not filename.strip():
        filename = "unnamed_file"

    return filename


def validate_content_safety(content: str, max_length: int = 10000) -> tuple[bool, Optional[str]]:
    """
    验证内容安全性

    Args:
        content: 待验证内容
        max_length: 最大长度

    Returns:
        (是否安全, 错误信息)
    """
    if not content:
        return False, "内容不能为空"

    # 长度检查
    if len(content) > max_length:
        return False, f"内容过长，最大允许{max_length}字符"

    # 检查是否包含NULL字节
    if "\x00" in content:
        return False, "内容包含非法字符(NULL byte)"

    # 检查是否包含过多控制字符（可能的二进制数据）
    control_chars = sum(1 for c in content if ord(c) < 32 and c not in "\n\r\t")
    if control_chars > len(content) * 0.1:  # 超过10%
        return False, "内容包含过多控制字符"

    return True, None


def sanitize_sql_identifier(identifier: str) -> str:
    """
    清理SQL标识符（表名、列名等）

    注意：本项目使用SQLAlchemy ORM，已自动防护SQL注入
    此函数仅用于需要动态构建SQL的特殊场景

    Args:
        identifier: SQL标识符

    Returns:
        清理后的标识符

    Raises:
        ValueError: 如果标识符不安全
    """
    import re

    # 只允许字母、数字、下划线
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", identifier):
        raise ValueError(f"不安全的SQL标识符: {identifier}")

    # 防止SQL关键字
    sql_keywords = {
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "EXEC",
        "EXECUTE",
        "UNION",
        "WHERE",
        "FROM",
    }

    if identifier.upper() in sql_keywords:
        raise ValueError(f"SQL标识符不能使用保留关键字: {identifier}")

    return identifier


# ==================== Request Logging ====================


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件（用于安全审计）"""

    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()

        # 记录请求信息
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
        )

        # 处理请求
        response = await call_next(request)

        # 记录响应信息
        duration_ms = int((time.time() - start_time) * 1000)

        log_level = "info"
        if response.status_code >= 500:
            log_level = "error"
        elif response.status_code >= 400:
            log_level = "warning"

        log_func = getattr(logger, log_level)
        log_func(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else "unknown",
        )

        return response


# ==================== CORS Security ====================


def get_cors_config(allowed_origins: list[str] | None = None):
    """
    获取CORS配置（开发环境和生产环境有不同配置）

    Args:
        allowed_origins: 允许的源列表（None表示使用默认配置）

    Returns:
        CORS配置字典
    """
    import os

    is_production = os.getenv("ENVIRONMENT", "development") == "production"

    if is_production:
        # 生产环境：严格的CORS配置
        return {
            "allow_origins": allowed_origins or [],  # 必须明确指定
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"],
            "max_age": 600,  # 10分钟
        }
    else:
        # 开发环境：宽松的CORS配置
        return {
            "allow_origins": ["http://localhost:*", "http://127.0.0.1:*"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
            "max_age": 3600,
        }


# ==================== Password/Token Validation ====================


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    验证密码强度（用于未来的用户认证功能）

    Args:
        password: 密码

    Returns:
        (是否符合要求, 错误信息)
    """
    if len(password) < 8:
        return False, "密码长度至少8个字符"

    if len(password) > 128:
        return False, "密码长度不能超过128个字符"

    # 检查是否包含至少一个数字
    if not any(c.isdigit() for c in password):
        return False, "密码必须包含至少一个数字"

    # 检查是否包含至少一个字母
    if not any(c.isalpha() for c in password):
        return False, "密码必须包含至少一个字母"

    # 检查是否包含至少一个特殊字符
    special_chars = set("!@#$%^&*()_+-=[]{}|;:,.<>?")
    if not any(c in special_chars for c in password):
        return False, "密码必须包含至少一个特殊字符"

    return True, None


def mask_sensitive_data(data: str, keep_chars: int = 4) -> str:
    """
    遮蔽敏感数据（用于日志记录）

    Args:
        data: 敏感数据
        keep_chars: 保留前后多少字符

    Returns:
        遮蔽后的数据

    Example:
        >>> mask_sensitive_data("secret_abc123def456", keep_chars=4)
        'secr************f456'
    """
    if not data or len(data) <= keep_chars * 2:
        return "*" * len(data) if data else ""

    masked_length = len(data) - (keep_chars * 2)
    return data[:keep_chars] + "*" * masked_length + data[-keep_chars:]
