"""
API Gateway Configuration
Per ARCHITECTURE.md: Environment-specific configurations
"""

from pydantic import BaseModel
from typing import Optional


class Settings(BaseModel):
    """API Gateway settings"""
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ipsakti"
    
    # Keycloak
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "ipsakti"
    keycloak_client_id: str = "ipsakti-api"
    
    # Orchestrator
    orchestrator_url: str = "http://localhost:8001"
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    
    # CORS
    cors_origins: list = ["http://localhost:5173"]
    
    # Logging
    log_level: str = "info"


settings = Settings()
