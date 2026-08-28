"""
Rate Limiting Middleware
Already configured in main.py using slowapi
This module provides additional rate limiting utilities
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
import logging

logger = logging.getLogger(__name__)

def get_user_id(request: Request) -> str:
    """
    Get user identifier for rate limiting
    Uses IP address by default, can be extended to use user ID
    """
    # Try to get user ID from request state if authenticated
    if hasattr(request.state, 'user') and request.state.user:
        return f"user:{request.state.user.get('user_id', 'anonymous')}"
    
    # Fall back to IP address
    return get_remote_address(request)

def create_rate_limiter():
    """
    Create a rate limiter instance
    """
    return Limiter(key_func=get_user_id)

# Rate limit configurations
RATE_LIMITS = {
    "public": "100/minute",      # General public endpoints
    "authenticated": "1000/minute",  # Authenticated users
    "admin": "10000/minute",     # Admin users
    "chat": "20/minute",         # Chat/conversation endpoints
    "search": "50/minute",       # Search/retrieval endpoints
}

async def check_rate_limit(request: Request, limit_type: str = "public"):
    """
    Check if request is within rate limits
    """
    # This is handled by slowapi decorator in main.py
    # This function can be used for custom rate limit logic
    pass
