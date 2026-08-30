"""
Embedding Generator
Generates embeddings using self-hosted models per ADR-001 and ADR-004
Uses BGE-large/E5-large baseline with support for reranker integration
"""

from typing import List, Dict, Any, Optional
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class EmbeddingGenerator:
    """
    Embedding generator using self-hosted models
    Per ADR-004: Uses BGE-large/E5-large baseline, not MiniLM
    """
    
    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5"):
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
        self.device = os.getenv("EMBEDDING_DEVICE", "cpu")
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the real embedding model using sentence-transformers"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"Loaded real embedding model: {self.model_name} on {self.device}")
        except ImportError:
            logger.error("sentence-transformers not installed. Cannot generate real embeddings.")
            raise
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for a list of chunks using the real BGE model
        """
        if self.model is None:
            raise RuntimeError("Embedding model not loaded")
        
        embedded_chunks = []
        
        for chunk in chunks:
            content = chunk["content"]
            
            # Generate real embedding using BGE model
            embedding = self.model.encode(content, convert_to_numpy=True)
            
            # Add embedding to chunk
            embedded_chunk = {
                **chunk,
                "embedding": embedding.tolist(),
                "embedding_model": self.model_name,
                "embedding_dimension": len(embedding)
            }
            embedded_chunks.append(embedded_chunk)
        
        logger.info(f"Generated real embeddings for {len(embedded_chunks)} chunks using {self.model_name}")
        return embedded_chunks
    
    def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text using the real BGE model
        """
        if self.model is None:
            raise RuntimeError("Embedding model not loaded")
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the embedding model
        """
        if self.model is None:
            return {
                "model_name": self.model_name,
                "dimension": 1024,  # BGE-large dimension
                "max_tokens": 512,  # Max token length
                "description": "Self-hosted embedding model per ADR-004",
                "status": "not_loaded"
            }
        
        return {
            "model_name": self.model_name,
            "dimension": self.model.get_sentence_embedding_dimension(),
            "max_tokens": 512,
            "description": "Self-hosted embedding model per ADR-004",
            "status": "loaded"
        }

# Global embedding generator instance
embedding_generator = EmbeddingGenerator()
