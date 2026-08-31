"""
API Gateway Configuration
Per ARCHITECTURE.md: Environment-specific configurations
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API Gateway settings"""
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/ip_sakti"
    
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
    cors_origins: str = "http://localhost:5173"
    
    # Logging
    log_level: str = "info"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
