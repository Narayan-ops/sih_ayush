"""
Health Check Routes
Provides health status and monitoring endpoints
"""

from fastapi import APIRouter, Request
import time
import logging
import os
import httpx

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
    orchestrator_healthy = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{os.getenv('ORCHESTRATOR_URL', 'http://localhost:8001')}/health")
            orchestrator_healthy = response.is_success and response.json().get("status") == "healthy"
    except Exception:
        logger.warning("Orchestrator health check failed", exc_info=True)
    return {
        "status": "healthy" if database_healthy and orchestrator_healthy else "degraded",
        "service": "api-gateway",
        "timestamp": time.time(),
        "components": {
            "api_gateway": "healthy",
            "database": "healthy" if database_healthy else "unhealthy",
            "orchestrator": "healthy" if orchestrator_healthy else "unhealthy",
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
    # A gateway must not accept research requests while its only downstream
    # authority is unhealthy; otherwise users receive opaque 503 failures.
    orchestrator_ready = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{os.getenv('ORCHESTRATOR_URL', 'http://localhost:8001')}/health")
            orchestrator_ready = response.is_success and response.json().get("status") == "healthy"
    except Exception:
        logger.warning("Orchestrator readiness check failed", exc_info=True)
    return {
        "ready": ready and orchestrator_ready,
        "components": {"database": ready, "orchestrator": orchestrator_ready},
        "timestamp": time.time()
    }

@router.get("/liveness")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {
        "alive": True,
        "timestamp": time.time()
    }
