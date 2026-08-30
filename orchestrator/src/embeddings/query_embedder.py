"""
Query Embedding Generator
Generates embeddings for user queries using the same model as ingestion
Per ADR-004: Uses BAAI/bge-large-en-v1.5 for consistency
"""

import logging
from typing import List
import os

logger = logging.getLogger(__name__)

class QueryEmbedder:
    """
    Embedding generator for user queries
    Uses the same model as ingestion to ensure consistency
    """
    
    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded query embedding model: {self.model_name}")
        except ImportError:
            logger.error("sentence-transformers not installed. Query embeddings will fail.")
            raise
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single query text
        """
        if self.model is None:
            raise RuntimeError("Embedding model not loaded")
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors"""
        if self.model is None:
            return 1024  # BAAI/bge-large-en-v1.5 dimension
        return self.model.get_sentence_embedding_dimension()

# Global query embedder instance
query_embedder = QueryEmbedder()
