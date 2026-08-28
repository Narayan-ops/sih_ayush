"""
IP-SAKTI Sahayak API Gateway
FastAPI Backend for Frontend (BFF)
Handles authentication, rate limiting, consent capture, and request routing
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
import logging
from contextlib import asynccontextmanager

from src.routes import chat, health

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("IP-SAKTI Sahayak API Gateway starting up...")
    yield
    # Shutdown
    logger.info("IP-SAKTI Sahayak API Gateway shutting down...")

app.router.lifespan_context = lifespan

# Include routers
app.include_router(health.router)
app.include_router(chat.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": time.time()
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "IP-SAKTI Sahayak API Gateway",
        "version": "0.1.0",
        "status": "operational",
        "description": "Backend for Frontend (BFF) for IP-SAKTI Sahayak"
    }

# Placeholder routes (to be implemented)
@app.get("/api/v1/status")
@limiter.limit("100/minute")
async def get_system_status(request: Request):
    """Get system status"""
    return {
        "status": "development",
        "phase": "MVP",
        "components": {
            "api_gateway": "operational",
            "orchestrator": "pending",
            "retrieval": "pending",
            "classification": "pending"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
