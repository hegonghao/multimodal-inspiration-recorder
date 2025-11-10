"""
Application Lifecycle Events
应用启动和关闭事件处理
"""

import logging
from typing import Callable
from fastapi import FastAPI

from src.database.connection import init_db, close_db

logger = logging.getLogger(__name__)


async def startup_handler():
    """
    Handle application startup events

    - Initialize database connection
    - Create database tables if not exist
    - Initialize Redis connection pool
    - Setup background tasks
    """
    logger.info("Starting application initialization...")

    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")

        # Initialize AI processor with user preferences from database
        try:
            from src.services.ai_processor import init_ai_processor_from_db
            await init_ai_processor_from_db()
            logger.info("AI processor initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize AI processor: {e}")

        # Additional startup tasks can be added here
        # - Redis connection pool
        # - Background task schedulers
        # - Cache warming

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise


async def shutdown_handler():
    """
    Handle application shutdown events

    - Close database connections
    - Close Redis connections
    - Cleanup background tasks
    - Flush logs
    """
    logger.info("Starting application shutdown...")

    try:
        # Close database connections
        await close_db()
        logger.info("Database connections closed")

        # Additional shutdown tasks can be added here
        # - Close Redis connections
        # - Cancel background tasks
        # - Flush metrics

    except Exception as e:
        logger.error(f"Shutdown error: {e}", exc_info=True)


def create_start_app_handler(app: FastAPI) -> Callable:
    """
    Create startup event handler for FastAPI application

    Args:
        app: FastAPI application instance

    Returns:
        Async callable for startup event
    """
    async def start_app() -> None:
        """Execute startup tasks"""
        await startup_handler()

    return start_app


def create_stop_app_handler(app: FastAPI) -> Callable:
    """
    Create shutdown event handler for FastAPI application

    Args:
        app: FastAPI application instance

    Returns:
        Async callable for shutdown event
    """
    async def stop_app() -> None:
        """Execute shutdown tasks"""
        await shutdown_handler()

    return stop_app
