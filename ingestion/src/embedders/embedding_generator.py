"""
Embedding Generator
Generates embeddings using self-hosted models per ADR-001 and ADR-004
Uses BGE-large/E5-large baseline with support for reranker integration
"""

from typing import List, Dict, Any, Optional
import logging
import hashlib

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """
    Embedding generator using self-hosted models
    Per ADR-004: Uses BGE-large/E5-large baseline, not MiniLM
    """
    
    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5"):
        self.model_name = model_name
        # Model would be loaded here in actual implementation
        # For now, we'll use a mock implementation
        logger.info(f"Initialized embedding generator with model: {model_name}")
    
    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for a list of chunks
        """
        embedded_chunks = []
        
        for chunk in chunks:
            content = chunk["content"]
            
            # Generate embedding (mock implementation)
            embedding = self._mock_generate_embedding(content)
            
            # Add embedding to chunk
            embedded_chunk = {
                **chunk,
                "embedding": embedding,
                "embedding_model": self.model_name,
                "embedding_dimension": len(embedding)
            }
            embedded_chunks.append(embedded_chunk)
        
        logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")
        return embedded_chunks
    
    def _mock_generate_embedding(self, text: str) -> List[float]:
        """
        Mock embedding generation for development
        In production, this would use the actual embedding model
        """
        # Generate a deterministic mock embedding based on text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hash to a 1024-dimensional vector (BGE-large dimension)
        embedding = []
        for i in range(1024):
            # Use hash bytes to generate consistent values
            byte_val = int(text_hash[i % len(text_hash)], 16)
            normalized_val = byte_val / 15.0  # Normalize to 0-1
            embedding.append(normalized_val)
        
        return embedding
    
    def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        """
        return self._mock_generate_embedding(text)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the embedding model
        """
        return {
            "model_name": self.model_name,
            "dimension": 1024,  # BGE-large dimension
            "max_tokens": 512,  # Max token length
            "description": "Self-hosted embedding model per ADR-004"
        }

# Global embedding generator instance
embedding_generator = EmbeddingGenerator()
