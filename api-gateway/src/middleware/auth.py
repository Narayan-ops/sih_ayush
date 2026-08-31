"""
Authentication and Authorization Middleware
Handles JWT validation and role-based access control
Integrates with Keycloak (self-hosted OAuth2/OIDC)
"""

from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
import logging
import os

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Role definitions
class Role:
    PUBLIC_USER = "public_user"
    PRACTITIONER = "practitioner"
    ADMIN = "admin"
    REVIEWER = "reviewer"

# Mock user data (replace with actual Keycloak integration)
DEV_AUTH_ENABLED = os.getenv("DEV_AUTH_ENABLED", "false").lower() == "true"
MOCK_USERS = {
    "test_token": {
        "user_id": "test_user_001",
        "roles": [Role.PUBLIC_USER],
        "permissions": ["read:basic"]
    }
}

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """
    Verify JWT token and return user information
    TODO: Integrate with Keycloak for actual token validation
    """
    token = credentials.credentials
    
    # Development tokens are deliberately opt-in.  They must never make a
    # deployed gateway accept a known credential.
    if DEV_AUTH_ENABLED and token in MOCK_USERS:
        return MOCK_USERS[token]
    
    if DEV_AUTH_ENABLED and token == "dev_test_token":
        return {
            "user_id": "dev_user",
            "roles": [Role.ADMIN],
            "permissions": ["*"]
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

def require_roles(allowed_roles: List[str]):
    """
    Decorator factory to require specific roles
    """
    async def role_checker(user: dict = Security(verify_token)):
        user_roles = user.get("roles", [])
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}"
            )
        return user
    return role_checker

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """
    Get current user if authenticated, return None otherwise
    Used for endpoints that work with both authenticated and anonymous users
    """
    if credentials is None:
        return None
    
    try:
        return await verify_token(credentials)
    except HTTPException:
        return None
