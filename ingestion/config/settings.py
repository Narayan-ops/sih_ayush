"""
Ingestion Configuration
Per ARCHITECTURE.md: Environment-specific configurations
"""

from pydantic import BaseModel
from typing import Optional


class Settings(BaseModel):
    """Ingestion settings"""
    
    # Vector Store
    qdrant_url: str = "http://localhost:6333"
    
    # Sparse Retrieval
    elasticsearch_url: str = "http://localhost:9200"
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ipsakti"
    
    # Document Store
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "ipsakti-documents"
    
    # Embedding Model
    embedding_model: str = "BAAI/bge-large-en-v1.5"  # Per ADR-004
    embedding_device: str = "cpu"
    
    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Batch Size
    batch_size: int = 100
    
    # Logging
    log_level: str = "info"


settings = Settings()
