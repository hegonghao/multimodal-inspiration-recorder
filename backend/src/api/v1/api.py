"""
API v1 Router

Aggregates all API route modules
"""

from fastapi import APIRouter

from src.api.v1.endpoints import records, sync, preferences, ai, health, analytics

api_router = APIRouter()

# Include route modules
api_router.include_router(records.router, prefix="/records", tags=["records"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(preferences.router, prefix="/preferences", tags=["preferences"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
