"""
Orchestrator Configuration
Per ARCHITECTURE.md: Environment-specific configurations
"""

from pydantic import BaseModel
from typing import Optional


class Settings(BaseModel):
    """Orchestrator settings"""
    
    # Vector Store
    qdrant_url: str = "http://localhost:6333"
    
    # Sparse Retrieval
    elasticsearch_url: str = "http://localhost:9200"
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ipsakti"
    
    # LLM Provider
    llm_provider: str = "self_hosted"  # Per ADR-001: Self-hosted default
    vllm_url: str = "http://localhost:8000"
    
    # Optional External Providers (require consent per ADR-001)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Embedding Model
    embedding_model: str = "BAAI/bge-large-en-v1.5"  # Per ADR-004
    
    # Reranker
    reranker_model: str = "BAAI/bge-reranker-large"
    
    # Confidence Thresholds
    min_retrieval_confidence: float = 0.6
    min_citation_confidence: float = 0.7
    min_overall_confidence: float = 0.65
    
    # Logging
    log_level: str = "info"


settings = Settings()
