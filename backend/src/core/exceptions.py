"""
Custom Exceptions
自定义异常类和错误处理
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.utils.logger import get_logger

logger = get_logger(__name__)


class BaseCustomException(Exception):
    """自定义异常基类"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class LLMServiceException(BaseCustomException):
    """LLM 服务异常"""
    pass


class RateLimitException(BaseCustomException):
    """速率限制异常"""
    pass


class AuthenticationException(BaseCustomException):
    """认证异常"""
    pass


class ValidationException(BaseCustomException):
    """验证异常"""
    pass


class ConfigurationException(BaseCustomException):
    """配置异常"""
    pass


class ExternalServiceException(BaseCustomException):
    """外部服务异常"""
    pass


class ResourceExhaustedException(BaseCustomException):
    """资源耗尽异常"""
    pass


class CircuitBreakerOpenException(BaseCustomException):
    """熔断器开启异常"""
    pass


async def llm_service_exception_handler(request: Request, exc: LLMServiceException):
    """LLM 服务异常处理器"""
    logger.error(f"LLM Service Exception: {exc.message}", extra={
        "error_code": exc.error_code,
        "details": exc.details,
        "path": request.url.path,
        "method": request.method
    })

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "LLM_SERVICE_ERROR",
            "message": "LLM 服务暂时不可用，请稍后重试",
            "error_code": exc.error_code,
            "details": exc.details,
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitException):
    """速率限制异常处理器"""
    logger.warning(f"Rate limit exceeded: {exc.message}", extra={
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host
    })

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "RATE_LIMIT_EXCEEDED",
            "message": "请求过于频繁，请稍后重试",
            "retry_after": 60,  # 建议重试时间（秒）
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        },
        headers={"Retry-After": "60"}
    )


async def authentication_exception_handler(request: Request, exc: AuthenticationException):
    """认证异常处理器"""
    logger.warning(f"Authentication failed: {exc.message}", extra={
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host
    })

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "AUTHENTICATION_FAILED",
            "message": "认证失败，请检查凭据",
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


async def validation_exception_handler(request: Request, exc: ValidationException):
    """验证异常处理器"""
    logger.warning(f"Validation failed: {exc.message}", extra={
        "error_code": exc.error_code,
        "details": exc.details,
        "path": request.url.path,
        "method": request.method
    })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "请求参数验证失败",
            "details": exc.details,
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


async def resource_exhausted_exception_handler(request: Request, exc: ResourceExhaustedException):
    """资源耗尽异常处理器"""
    logger.error(f"Resource exhausted: {exc.message}", extra={
        "error_code": exc.error_code,
        "details": exc.details,
        "path": request.url.path,
        "method": request.method
    })

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "RESOURCE_EXHAUSTED",
            "message": "服务资源暂时耗尽，请稍后重试",
            "details": exc.details,
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


async def circuit_breaker_exception_handler(request: Request, exc: CircuitBreakerOpenException):
    """熔断器开启异常处理器"""
    logger.warning(f"Circuit breaker open: {exc.message}", extra={
        "path": request.url.path,
        "method": request.method
    })

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "SERVICE_UNAVAILABLE",
            "message": "服务暂时不可用，正在进行故障恢复",
            "retry_after": 30,
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        },
        headers={"Retry-After": "30"}
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 异常处理器"""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}", extra={
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host
    })

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理器"""
    logger.warning(f"Request validation error: {exc.errors()}", extra={
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host
    })

    # 格式化验证错误
    formatted_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "请求数据格式不正确",
            "details": {"validation_errors": formatted_errors},
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}", extra={
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host,
        "exc_info": True
    })

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误，请联系管理员",
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


def setup_exception_handlers(app):
    """设置异常处理器"""
    # 自定义异常处理器
    app.add_exception_handler(LLMServiceException, llm_service_exception_handler)
    app.add_exception_handler(RateLimitException, rate_limit_exception_handler)
    app.add_exception_handler(AuthenticationException, authentication_exception_handler)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(ResourceExhaustedException, resource_exhausted_exception_handler)
    app.add_exception_handler(CircuitBreakerOpenException, circuit_breaker_exception_handler)

    # FastAPI 内置异常处理器
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    # 通用异常处理器（最后注册）
    app.add_exception_handler(Exception, general_exception_handler)