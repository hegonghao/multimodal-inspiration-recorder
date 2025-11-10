"""
FastAPI Application Main Entry Point (ALTERNATIVE)

⚠️ WARNING: This is an ALTERNATIVE entry point created during refactoring.
⚠️ The PRIMARY/CANONICAL entry point is: backend/src/main.py

This entry point uses enhanced security middleware but is missing AI and health routers.
See docs/quickstart_validation_report.md for architectural inconsistency details.

TODO: Consolidate with src/main.py (target: post-MVP)

This module initializes the FastAPI application and configures:
- API routes (records, sync, preferences only)
- Middleware (Security, CORS, Error Handling) - enhanced implementation
- Exception handlers
- Startup/shutdown events
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.endpoints import records, sync, preferences
from src.api.middleware.error_handler import add_error_handlers
from src.api.middleware.security import (
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    get_cors_config,
)
from src.core.events import create_start_app_handler, create_stop_app_handler
from src.config import settings


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    application = FastAPI(
        title="多模输入灵感记录器 API",
        description="Multimodal Inspiration Recorder Backend API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware (environment-aware configuration)
    cors_config = get_cors_config(settings.ALLOWED_ORIGINS if settings.ALLOWED_ORIGINS != ["*"] else None)
    application.add_middleware(CORSMiddleware, **cors_config)

    # Add security middleware (order matters: logging → security headers → size limit → rate limit)
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestSizeLimitMiddleware, max_request_size=50 * 1024 * 1024)  # 50MB
    application.add_middleware(RateLimitMiddleware)

    # Add error handlers
    add_error_handlers(application)

    # Register API routes
    application.include_router(
        records.router,
        prefix="/api/v1/records",
        tags=["Records"],
    )
    application.include_router(
        sync.router,
        prefix="/api/v1/sync",
        tags=["Sync"],
    )
    application.include_router(
        preferences.router,
        prefix="/api/v1/preferences",
        tags=["Preferences"],
    )

    # Add event handlers
    application.add_event_handler("startup", create_start_app_handler(application))
    application.add_event_handler("shutdown", create_stop_app_handler(application))

    return application


# Create application instance
app = create_application()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Multimodal Inspiration Recorder API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
