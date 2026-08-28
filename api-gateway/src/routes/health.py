"""
Health Check Routes
Provides health status and monitoring endpoints
"""

from fastapi import APIRouter
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
async def detailed_health_check():
    """Detailed health check with component status"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": time.time(),
        "components": {
            "api_gateway": "healthy",
            "database": "not_configured",
            "orchestrator": "not_connected",
            "auth": "mock_mode"
        }
    }

@router.get("/readiness")
async def readiness_check():
    """Readiness check for Kubernetes"""
    return {
        "ready": True,
        "timestamp": time.time()
    }

@router.get("/liveness")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {
        "alive": True,
        "timestamp": time.time()
    }
