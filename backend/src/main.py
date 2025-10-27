"""
FastAPI Application Entry Point
多模输入灵感记录器后端服务
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging

from src.core.events import startup_handler, shutdown_handler
from src.core.middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware
)
from src.core.exceptions import setup_exception_handlers
from src.api.v1.api import api_router
from src.config import settings
from src.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await startup_handler()
    logger.info("FastAPI application started successfully")

    yield

    # Shutdown
    await shutdown_handler()
    logger.info("FastAPI application shutdown complete")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="多模输入灵感记录器 API",
        description="Multi-modal input inspiration recorder backend service",
        version="1.0.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    )

    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security middleware
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )

    # Custom middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Exception handlers
    setup_exception_handlers(app)

    # Include API routers
    app.include_router(api_router, prefix="/api/v1")

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Basic health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0"
        }

    return app


# Create application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )