"""
Cross-Encoder Reranker for result refinement
Uses BGE-reranker-large or equivalent for semantic reranking
"""

import os
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    # Placeholder for when sentence-transformers is installed
    CrossEncoder = None

logger = logging.getLogger(__name__)


@dataclass
class RerankedResult:
    """Represents a reranked retrieval result"""
    chunk_id: str
    source_id: str
    section: str
    article: str
    text: str
    original_score: float
    rerank_score: float
    version_hash: str
    jurisdiction: str
    domain: str
    metadata: Dict


class CrossEncoderReranker:
    """
    Cross-encoder reranker for refining retrieval results
    
    Uses BGE-reranker-large or equivalent to rerank dense + sparse results
    Improves precision for legal document retrieval
    """

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize cross-encoder model
        
        Args:
            model_name: Model name (default: BAAI/bge-reranker-large)
            device: Device to run on (cuda/cpu)
        """
        self.model_name = model_name or os.getenv(
            "RERANKER_MODEL", 
            "BAAI/bge-reranker-large"
        )
        self.device = device or os.getenv("RERANKER_DEVICE", "cpu")
        
        if CrossEncoder is None:
            logger.warning("sentence-transformers not installed. Reranker will be non-functional.")
            self.model = None
        else:
            try:
                self.model = CrossEncoder(self.model_name, device=self.device)
                logger.info(f"CrossEncoderReranker initialized with {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load reranker model: {e}")
                self.model = None

    def rerank(
        self,
        query: str,
        results: List,
        top_k: Optional[int] = None
    ) -> List[RerankedResult]:
        """
        Rerank retrieval results using cross-encoder
        
        Args:
            query: Original query text
            results: List of retrieval results (dense or sparse)
            top_k: Number of top results to return (None = all)
            
        Returns:
            Reranked results sorted by cross-encoder score
        """
        if self.model is None:
            logger.warning("Reranker model not loaded. Returning original results.")
            # Return as-is with rerank_score = original_score
            return self._fallback_rerank(results)
        
        if not results:
            return []
        
        # Prepare pairs for cross-encoder
        pairs = [(query, result.text) for result in results]
        
        try:
            # Compute cross-encoder scores
            scores = self.model.predict(pairs)
            
            # Combine with original results
            reranked = []
            for result, score in zip(results, scores):
                reranked.append(RerankedResult(
                    chunk_id=result.chunk_id,
                    source_id=result.source_id,
                    section=result.section,
                    article=result.article,
                    text=result.text,
                    original_score=result.score,
                    rerank_score=float(score),
                    version_hash=result.version_hash,
                    jurisdiction=result.jurisdiction,
                    domain=result.domain,
                    metadata=result.metadata
                ))
            
            # Sort by rerank score
            reranked.sort(key=lambda x: x.rerank_score, reverse=True)
            
            # Return top_k if specified
            if top_k is not None:
                reranked = reranked[:top_k]
            
            logger.info(f"Reranked {len(results)} results, returning top {len(reranked)}")
            return reranked
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            return self._fallback_rerank(results)

    def rerank_hybrid(
        self,
        query: str,
        dense_results: List,
        sparse_results: List,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
        top_k: int = 10
    ) -> List[RerankedResult]:
        """
        Rerank combined dense + sparse results with weighted fusion
        
        Args:
            query: Original query
            dense_results: Dense retrieval results
            sparse_results: Sparse retrieval results
            dense_weight: Weight for dense results
            sparse_weight: Weight for sparse results
            top_k: Number of results to return
            
        Returns:
            Reranked and fused results
        """
        if self.model is None:
            # Simple fusion without reranking
            return self._simple_fusion(
                dense_results, 
                sparse_results, 
                dense_weight, 
                sparse_weight, 
                top_k
            )
        
        # Deduplicate by chunk_id
        seen_ids = set()
        combined = []
        
        for result in dense_results:
            if result.chunk_id not in seen_ids:
                seen_ids.add(result.chunk_id)
                combined.append(('dense', result))
        
        for result in sparse_results:
            if result.chunk_id not in seen_ids:
                seen_ids.add(result.chunk_id)
                combined.append(('sparse', result))
        
        if not combined:
            return []
        
        # Rerank combined results
        pairs = [(query, result[1].text) for result in combined]
        scores = self.model.predict(pairs)
        
        # Apply weighted scores
        reranked = []
        for (source_type, result), score in zip(combined, scores):
            weight = dense_weight if source_type == 'dense' else sparse_weight
            adjusted_score = float(score) * weight
            
            reranked.append(RerankedResult(
                chunk_id=result.chunk_id,
                source_id=result.source_id,
                section=result.section,
                article=result.article,
                text=result.text,
                original_score=result.score,
                rerank_score=adjusted_score,
                version_hash=result.version_hash,
                jurisdiction=result.jurisdiction,
                domain=result.domain,
                metadata=result.metadata
            ))
        
        # Sort by rerank score
        reranked.sort(key=lambda x: x.rerank_score, reverse=True)
        
        return reranked[:top_k]

    def _fallback_rerank(self, results: List) -> List[RerankedResult]:
        """Fallback when model is not loaded"""
        reranked = []
        for result in results:
            reranked.append(RerankedResult(
                chunk_id=result.chunk_id,
                source_id=result.source_id,
                section=result.section,
                article=result.article,
                text=result.text,
                original_score=result.score,
                rerank_score=result.score,
                version_hash=result.version_hash,
                jurisdiction=result.jurisdiction,
                domain=result.domain,
                metadata=result.metadata
            ))
        
        reranked.sort(key=lambda x: x.rerank_score, reverse=True)
        return reranked

    def _simple_fusion(
        self,
        dense_results: List,
        sparse_results: List,
        dense_weight: float,
        sparse_weight: float,
        top_k: int
    ) -> List[RerankedResult]:
        """Simple score fusion without reranking"""
        # Combine and deduplicate
        seen_ids = {}
        
        for result in dense_results:
            if result.chunk_id not in seen_ids:
                seen_ids[result.chunk_id] = (result, dense_weight)
            else:
                # Prefer dense if duplicate
                seen_ids[result.chunk_id] = (result, dense_weight)
        
        for result in sparse_results:
            if result.chunk_id not in seen_ids:
                seen_ids[result.chunk_id] = (result, sparse_weight)
        
        # Apply weights
        fused = []
        for result, weight in seen_ids.values():
            fused.append(RerankedResult(
                chunk_id=result.chunk_id,
                source_id=result.source_id,
                section=result.section,
                article=result.article,
                text=result.text,
                original_score=result.score,
                rerank_score=result.score * weight,
                version_hash=result.version_hash,
                jurisdiction=result.jurisdiction,
                domain=result.domain,
                metadata=result.metadata
            ))
        
        fused.sort(key=lambda x: x.rerank_score, reverse=True)
        return fused[:top_k]

    def health_check(self) -> bool:
        """Check if reranker model is loaded"""
        if self.model is None:
            return False
        
        try:
            # Test prediction
            test_score = self.model.predict([("test", "test query")])
            logger.info(f"Reranker health check passed. Test score: {test_score[0]}")
            return True
        except Exception as e:
            logger.error(f"Reranker health check failed: {e}")
            return False
