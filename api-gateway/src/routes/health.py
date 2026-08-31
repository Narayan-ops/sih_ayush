"""
Health Check Routes
Provides health status and monitoring endpoints
"""

from fastapi import APIRouter, Request
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": time.time()
    }

@router.get("/detailed")
async def detailed_health_check(request: Request):
    """Detailed health check with component status"""
    database_healthy = False
    try:
        async with request.app.state.repository.pool.acquire() as conn:
            database_healthy = (await conn.fetchval("SELECT 1")) == 1
    except Exception:
        logger.exception("Database health check failed")
    return {
        "status": "healthy" if database_healthy else "degraded",
        "service": "api-gateway",
        "timestamp": time.time(),
        "components": {
            "api_gateway": "healthy",
            "database": "healthy" if database_healthy else "unhealthy",
            "orchestrator": "not_checked",
            "auth": "configured"
        }
    }

@router.get("/readiness")
async def readiness_check(request: Request):
    """Readiness check for Kubernetes"""
    ready = False
    try:
        async with request.app.state.repository.pool.acquire() as conn:
            ready = (await conn.fetchval("SELECT 1")) == 1
    except Exception:
        logger.exception("Readiness database check failed")
    return {
        "ready": ready,
        "timestamp": time.time()
    }

@router.get("/liveness")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {
        "alive": True,
        "timestamp": time.time()
    }
