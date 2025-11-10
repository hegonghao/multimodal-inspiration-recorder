"""
Error Handler Middleware

Provides centralized error handling for all API requests
"""

import time
import traceback
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.utils.logger import get_logger
from src.core.exceptions import ExternalServiceException

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for centralized error handling and logging

    Features:
    - Catches all unhandled exceptions
    - Logs errors with request context
    - Returns consistent error responses
    - Adds request timing information
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and handle any errors
        """
        # Add request start time
        request.state.start_time = time.time()

        try:
            # Process the request
            response = await call_next(request)

            # Add response time header
            process_time = time.time() - request.state.start_time
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as exc:
            # Calculate request processing time
            process_time = time.time() - request.state.start_time

            # Log the error with full context
            logger.error(
                f"Unhandled exception in request: {type(exc).__name__}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else "unknown",
                    "process_time": process_time,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "traceback": traceback.format_exc(),
                },
                exc_info=True
            )

            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "timestamp": time.time(),
                    "request_id": getattr(request.state, "request_id", None),
                },
                headers={
                    "X-Process-Time": str(process_time),
                }
            )


def add_error_handlers(app: FastAPI) -> None:
    """
    Add exception handlers to FastAPI application

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions"""
        logger.warning(
            f"HTTP exception: {exc.status_code}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code,
                "detail": exc.detail,
            }
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "timestamp": time.time(),
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors"""
        logger.warning(
            "Request validation error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "errors": exc.errors(),
            }
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Invalid request data",
                "details": exc.errors(),
                "timestamp": time.time(),
            }
        )

    @app.exception_handler(ExternalServiceException)
    async def external_service_exception_handler(request: Request, exc: ExternalServiceException):
        """Handle external service errors"""
        logger.error(
            f"External service error: {exc.error_code}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error_code": exc.error_code,
                "message": exc.message,
            }
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "timestamp": time.time(),
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions"""
        logger.error(
            f"Unhandled exception: {type(exc).__name__}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": traceback.format_exc(),
            },
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": time.time(),
            }
        )
