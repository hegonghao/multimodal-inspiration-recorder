"""
Health Check API Endpoints
Provides comprehensive health monitoring for production deployment
"""
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from src.database.connection import get_db
from src.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", summary="Basic health check")
async def basic_health() -> Dict[str, Any]:
    """
    Basic health check endpoint
    Returns 200 if service is alive
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "inspiration-recorder-api",
        "version": "1.0.0",
    }


@router.get("/readiness", summary="Readiness check for Kubernetes")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Readiness check endpoint - verifies service can accept traffic
    Used by Kubernetes/load balancers to determine if pod is ready
    Returns 200 if ready, 503 if not ready
    """
    checks = {
        "database": False,
        "config": False,
    }
    errors = []

    # Check database connectivity
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        checks["database"] = True
    except Exception as e:
        errors.append(f"Database: {str(e)}")
        logger.error(f"Database readiness check failed: {e}")

    # Check configuration
    try:
        if settings.SECRET_KEY and len(settings.SECRET_KEY) >= 32:
            checks["config"] = True
        else:
            errors.append("Configuration: SECRET_KEY not properly set")
    except Exception as e:
        errors.append(f"Configuration: {str(e)}")
        logger.error(f"Config readiness check failed: {e}")

    # Determine overall readiness
    all_ready = all(checks.values())

    response = {
        "status": "ready" if all_ready else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }

    if errors:
        response["errors"] = errors

    if not all_ready:
        raise HTTPException(status_code=503, detail=response)

    return response


@router.get("/liveness", summary="Liveness check for Kubernetes")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint - verifies process is alive
    Used by Kubernetes to detect if pod needs restart
    Returns 200 if alive
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/version", summary="Mobile app update information")
async def mobile_app_version() -> Dict[str, Any]:
    """Return the latest mobile build configured by the server operator."""
    return {
        "latest_version": settings.MOBILE_APP_VERSION,
        "latest_build": settings.MOBILE_APP_BUILD,
        "download_url": settings.MOBILE_APP_APK_URL,
        "release_notes": settings.MOBILE_APP_RELEASE_NOTES,
        "force_update": settings.MOBILE_APP_FORCE_UPDATE,
    }


@router.get("/startup", summary="Startup check for Kubernetes")
async def startup_check(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Startup check endpoint - verifies initialization complete
    Used by Kubernetes during initial pod startup
    Returns 200 when startup complete, 503 during startup
    """
    checks = {
        "database_connected": False,
        "tables_exist": False,
        "config_loaded": False,
    }
    errors = []

    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        checks["database_connected"] = True
    except Exception as e:
        errors.append(f"Database connection: {str(e)}")

    # Check if main tables exist (migrations applied)
    try:
        result = await db.execute(
            text("SELECT COUNT(*) FROM inspiration_records LIMIT 1")
        )
        result.scalar_one()
        checks["tables_exist"] = True
    except Exception as e:
        errors.append(f"Database tables: {str(e)}")

    # Check config loaded
    try:
        if settings.SECRET_KEY:
            checks["config_loaded"] = True
    except Exception as e:
        errors.append(f"Configuration: {str(e)}")

    all_started = all(checks.values())

    response = {
        "status": "started" if all_started else "starting",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }

    if errors:
        response["errors"] = errors

    if not all_started:
        raise HTTPException(status_code=503, detail=response)

    return response


@router.get("/detailed", summary="Detailed health status")
async def detailed_health(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Detailed health check with comprehensive metrics
    Includes status of all dependencies and subsystems
    """
    checks = {}

    # Database health with stats
    try:
        # Connection check
        await db.execute(text("SELECT 1"))

        # Get record counts
        result = await db.execute(text("SELECT COUNT(*) FROM inspiration_records"))
        total_records = result.scalar_one()

        result = await db.execute(
            text("SELECT COUNT(*) FROM inspiration_records WHERE sync_status = 0")
        )
        pending_sync = result.scalar_one()

        checks["database"] = {
            "status": "healthy",
            "connected": True,
            "total_records": total_records,
            "pending_sync": pending_sync,
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
        }
        logger.error(f"Database health check failed: {e}")

    # Configuration health
    try:
        checks["configuration"] = {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "debug_mode": settings.DEBUG,
            "features": {
                "voice_input": settings.ENABLE_VOICE_INPUT,
                "image_ocr": settings.ENABLE_IMAGE_OCR,
                "text_input": settings.ENABLE_TEXT_INPUT,
                "notion_sync": settings.ENABLE_NOTION_SYNC,
                "ai_processing": settings.ENABLE_AI_PROCESSING,
            },
            "api_keys_configured": {
                "openai": bool(settings.OPENAI_API_KEY),
                "deepgram": bool(settings.DEEPGRAM_API_KEY),
                "notion": bool(settings.NOTION_TOKEN or settings.NOTION_API_KEY),
            },
        }
    except Exception as e:
        checks["configuration"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        logger.error(f"Configuration health check failed: {e}")

    # Redis health
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )
        await redis_client.ping()

        info = await redis_client.info()
        checks["redis"] = {
            "status": "healthy",
            "connected": True,
            "version": info.get("redis_version", "unknown"),
            "used_memory": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
        }
        await redis_client.close()
    except Exception as e:
        checks["redis"] = {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
        }
        logger.warning(f"Redis health check failed (optional): {e}")

    # Determine overall health
    critical_checks = ["database", "configuration"]
    overall_healthy = all(
        checks.get(check, {}).get("status") == "healthy" for check in critical_checks
    )

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": checks.get("configuration", {}).get("environment", "unknown"),
        "checks": checks,
    }
