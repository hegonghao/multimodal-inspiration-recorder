"""
Custom Middleware Components
自定义中间件组件
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging middleware
    记录所有请求的详细信息
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timer
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log request info
            logger.info(
                f"{request.method} {request.url.path} "
                f"status={response.status_code} "
                f"duration={duration:.3f}s"
            )

            # Add custom headers
            response.headers["X-Process-Time"] = str(duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"{request.method} {request.url.path} "
                f"error={str(e)} "
                f"duration={duration:.3f}s",
                exc_info=True
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware
    限制请求频率（简单实现）
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Simple in-memory rate limiter
        # In production, use Redis-based rate limiter
        self.request_counts = {}
        self.window_size = 60  # 60 seconds
        self.max_requests = 100  # 100 requests per window

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Simple rate limiting (should use Redis in production)
        # For now, just pass through

        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware
    添加安全相关的 HTTP 头
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
