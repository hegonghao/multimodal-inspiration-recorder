"""
Centralized Logging Configuration
统一日志配置

This module provides a centralized configuration for all logging in the application.
It supports both structured (JSON) and human-readable (Console) logging formats.
"""

import sys
import logging
from typing import Any, Dict
import structlog
from structlog.types import Processor

from src.config import settings


def add_app_context(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add application context to log events

    Args:
        logger: Logger instance
        method_name: Method name
        event_dict: Event dictionary

    Returns:
        Updated event dictionary with app context
    """
    event_dict["app"] = settings.APP_NAME
    event_dict["version"] = settings.VERSION
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def configure_logging() -> None:
    """
    Configure structured logging for the entire application

    This function should be called once at application startup.
    It configures both the standard library logging and structlog.
    """

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Silence noisy loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Determine processors based on environment
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        add_app_context,
    ]

    # Choose renderer based on log format setting
    if settings.LOG_FORMAT == "json":
        # JSON format for production (structured logging)
        processors = shared_processors + [
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console format for development (human-readable)
        processors = shared_processors + [
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    Example:
        >>> from src.core.logging_config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("application_started", port=8000)
    """
    return structlog.get_logger(name)


def log_request_info(
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    client_ip: str = "unknown",
) -> None:
    """
    Log HTTP request information in a standardized format

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        client_ip: Client IP address

    Example:
        >>> log_request_info("POST", "/api/v1/records", 201, 125, "192.168.1.1")
    """
    logger = get_logger("http")

    log_level = "info"
    if status_code >= 500:
        log_level = "error"
    elif status_code >= 400:
        log_level = "warning"

    log_func = getattr(logger, log_level)
    log_func(
        "http_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        client_ip=client_ip,
    )


def log_ai_processing(
    record_id: int,
    input_type: str,
    duration_ms: int,
    success: bool,
    error: str = None,
) -> None:
    """
    Log AI processing events

    Args:
        record_id: Record ID being processed
        input_type: Input type (voice/text/image)
        duration_ms: Processing duration in milliseconds
        success: Whether processing succeeded
        error: Error message if failed

    Example:
        >>> log_ai_processing(1, "voice", 1250, True)
        >>> log_ai_processing(2, "text", 500, False, "LLM API timeout")
    """
    logger = get_logger("ai_processing")

    if success:
        logger.info(
            "ai_processing_completed",
            record_id=record_id,
            input_type=input_type,
            duration_ms=duration_ms,
        )
    else:
        logger.error(
            "ai_processing_failed",
            record_id=record_id,
            input_type=input_type,
            duration_ms=duration_ms,
            error=error,
        )


def log_sync_event(
    record_id: int,
    operation: str,
    status: str,
    retry_count: int = 0,
    error: str = None,
) -> None:
    """
    Log Notion sync events

    Args:
        record_id: Record ID being synced
        operation: Sync operation (create/update/delete)
        status: Sync status (pending/processing/completed/failed)
        retry_count: Number of retries attempted
        error: Error message if failed

    Example:
        >>> log_sync_event(1, "create", "completed")
        >>> log_sync_event(2, "update", "failed", retry_count=3, error="Network timeout")
    """
    logger = get_logger("sync")

    if status == "completed":
        logger.info(
            "sync_completed",
            record_id=record_id,
            operation=operation,
            retry_count=retry_count,
        )
    elif status == "failed":
        logger.error(
            "sync_failed",
            record_id=record_id,
            operation=operation,
            retry_count=retry_count,
            error=error,
        )
    else:
        logger.debug(
            "sync_status_changed",
            record_id=record_id,
            operation=operation,
            status=status,
        )


# Initialize logging on module import
if settings.DEBUG or settings.ENVIRONMENT == "development":
    # In development, configure immediately for visibility
    configure_logging()
