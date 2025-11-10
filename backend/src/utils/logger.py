"""
Logging Configuration
日志配置和管理
"""

import logging
import logging.handlers
import sys
import json
from typing import Any, Dict
from datetime import datetime

import structlog
from pythonjsonlogger import jsonlogger

from src.config import settings


def setup_logging():
    """设置应用日志"""
    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # 清除现有处理器
    root_logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    if settings.LOG_FORMAT == "json":
        # JSON 格式
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    else:
        # 文本格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 如果是生产环境，添加文件处理器
    if settings.ENVIRONMENT == "production":
        file_handler = logging.handlers.RotatingFileHandler(
            "src.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 设置第三方库的日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    # 配置 Sentry（如果配置了 DSN）
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.httpx import HttpxIntegration

            sentry_logging = LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            )

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                integrations=[
                    sentry_logging,
                    FastApiIntegration(),
                    HttpxIntegration(),
                ],
                traces_sample_rate=0.1,
                environment=settings.ENVIRONMENT
            )
        except ImportError:
            logging.warning("Sentry SDK not installed, skipping Sentry configuration")


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取结构化日志器"""
    return structlog.get_logger(name)


class RequestLogger:
    """请求日志记录器"""

    def __init__(self, logger_name: str = "request"):
        self.logger = get_logger(logger_name)

    def log_request(
        self,
        method: str,
        path: str,
        query_params: Dict[str, Any],
        headers: Dict[str, str],
        client_ip: str,
        user_agent: str,
        request_id: str
    ):
        """记录请求日志"""
        self.logger.info(
            "Request received",
            extra={
                "event": "request_received",
                "method": method,
                "path": path,
                "query_params": query_params,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
        )

    def log_response(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        request_id: str
    ):
        """记录响应日志"""
        level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
        getattr(self.logger, level)(
            "Response sent",
            extra={
                "event": "response_sent",
                "method": method,
                "path": path,
                "status_code": status_code,
                "response_time": response_time,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
        )

    def log_error(
        self,
        method: str,
        path: str,
        error: Exception,
        request_id: str
    ):
        """记录错误日志"""
        self.logger.error(
            "Request error",
            extra={
                "event": "request_error",
                "method": method,
                "path": path,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            },
            exc_info=True
        )


class PerformanceLogger:
    """性能日志记录器"""

    def __init__(self, logger_name: str = "performance"):
        self.logger = get_logger(logger_name)

    def log_slow_query(
        self,
        query_type: str,
        duration: float,
        parameters: Dict[str, Any]
    ):
        """记录慢查询"""
        self.logger.warning(
            "Slow query detected",
            extra={
                "event": "slow_query",
                "query_type": query_type,
                "duration": duration,
                "parameters": parameters,
                "timestamp": datetime.now().isoformat()
            }
        )

    def log_external_api_call(
        self,
        service: str,
        endpoint: str,
        method: str,
        duration: float,
        status_code: int,
        error: str = None
    ):
        """记录外部 API 调用"""
        level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
        getattr(self.logger, level)(
            "External API call",
            extra={
                "event": "external_api_call",
                "service": service,
                "endpoint": endpoint,
                "method": method,
                "duration": duration,
                "status_code": status_code,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
        )

    def log_cache_hit_miss(
        self,
        cache_key: str,
        hit: bool,
        backend: str
    ):
        """记录缓存命中/未命中"""
        level = "debug" if hit else "info"
        getattr(self.logger, level)(
            "Cache access",
            extra={
                "event": "cache_access",
                "cache_key": cache_key,
                "hit": hit,
                "backend": backend,
                "timestamp": datetime.now().isoformat()
            }
        )


class SecurityLogger:
    """安全日志记录器"""

    def __init__(self, logger_name: str = "security"):
        self.logger = get_logger(logger_name)

    def log_authentication_attempt(
        self,
        client_ip: str,
        user_agent: str,
        success: bool,
        error: str = None
    ):
        """记录认证尝试"""
        level = "info" if success else "warning"
        getattr(self.logger, level)(
            "Authentication attempt",
            extra={
                "event": "authentication_attempt",
                "client_ip": client_ip,
                "user_agent": user_agent,
                "success": success,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
        )

    def log_rate_limit_violation(
        self,
        client_ip: str,
        endpoint: str,
        limit: int,
        window: int
    ):
        """记录速率限制违规"""
        self.logger.warning(
            "Rate limit violation",
            extra={
                "event": "rate_limit_violation",
                "client_ip": client_ip,
                "endpoint": endpoint,
                "limit": limit,
                "window": window,
                "timestamp": datetime.now().isoformat()
            }
        )

    def log_suspicious_activity(
        self,
        activity_type: str,
        client_ip: str,
        details: Dict[str, Any]
    ):
        """记录可疑活动"""
        self.logger.error(
            "Suspicious activity detected",
            extra={
                "event": "suspicious_activity",
                "activity_type": activity_type,
                "client_ip": client_ip,
                "details": details,
                "timestamp": datetime.now().isoformat()
            }
        )