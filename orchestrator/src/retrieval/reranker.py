"""
Cross-Encoder Reranker for result refinement
Uses BGE-reranker-large or equivalent for semantic reranking
"""

import os
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import CrossEncoder
    logger.info("Successfully imported CrossEncoder from sentence-transformers")
except ImportError as e:
    # Placeholder for when sentence-transformers is installed
    logger.error(f"Failed to import sentence-transformers: {e}")
    CrossEncoder = None


def _extract_explicit_reference(query: str) -> Optional[str]:
    """
    Extract explicit clause/section reference from query if present.
    
    Patterns:
    - "Section 3(p)" -> "3(p)"
    - "3(p)" -> "3(p)"
    - "clause 3(p)" -> "3(p)"
    - "Section 3" -> "3"
    
    Returns:
        Extracted reference string (e.g., "3(p)", "3") or None if no match
    """
    # Pattern for clause references like 3(p), 3(a), etc.
    clause_pattern = re.compile(r'(?:section|clause)?\s*(\d+\([a-z]\))', re.IGNORECASE)
    match = clause_pattern.search(query)
    if match:
        return match.group(1)
    
    # Pattern for simple section references like "Section 3", "3"
    # Only match if NOT followed by a parenthesis (to avoid matching "3" in "3(p)")
    section_pattern = re.compile(r'(?:section|clause)?\s*(\d+)(?!\s*\()', re.IGNORECASE)
    match = section_pattern.search(query)
    if match:
        return match.group(1)
    
    return None


@dataclass
class RerankedResult:
    """Represents a reranked retrieval result"""
    chunk_id: str
    source_id: str
    section: str
    article: str
    content: str  # Changed from text to content to match ingestion
    original_score: float
    rerank_score: float
    version_hash: str
    jurisdiction: str
    domain: str
    metadata: Dict
    clause: str = ""  # Added clause field for exact-match boost


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
        pairs = [(query, result.content) for result in results]
        
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
                    content=result.content,
                    original_score=result.score if hasattr(result, 'score') else result.get('score', 0.0),
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
                top_k,
                query
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
        pairs = [(query, result[1].content) for result in combined]
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
                content=result.content,
                original_score=result.score if hasattr(result, 'score') else result.get('score', 0.0),
                rerank_score=adjusted_score,
                version_hash=result.version_hash,
                jurisdiction=result.jurisdiction,
                domain=result.domain,
                metadata=result.metadata,
                clause=getattr(result, 'clause', '') or result.metadata.get('clause', '')
            ))
        
        # Apply exact-match boost for explicit clause/section references
        explicit_ref = _extract_explicit_reference(query)
        if explicit_ref:
            logger.info(f"Query contains explicit reference: {explicit_ref}")
            boosted_count = 0
            for result in reranked:
                # Check if result's clause or section matches the explicit reference
                result_clause = getattr(result, 'clause', '')
                result_section = str(result.section)
                
                if explicit_ref in result_clause or explicit_ref == result_section:
                    # Apply 5x boost for exact match
                    result.rerank_score *= 5.0
                    boosted_count += 1
                    logger.info(f"Boosted chunk_id={result.chunk_id[:8]}..., clause={result_clause}, section={result_section}, ref={explicit_ref}, new_score={result.rerank_score:.4f}")
            
            if boosted_count > 0:
                logger.info(f"Applied exact-match boost to {boosted_count} results")
        
        # Apply definition chunk boost for "What is X" queries (but not "What are X" queries)
        import re
        # Only match "What is X" or "What is a X", not "What are X"
        definition_match = re.search(r'what\s+is\s+(?:a\s+)?([a-z_]+(?:\s+[a-z_]+)?)(?:\s+under|$)', query, re.IGNORECASE)
        if definition_match:
            definition_term = definition_match.group(1).strip().lower()
            # Normalize: replace spaces with underscores for clause matching
            definition_term_normalized = definition_term.replace(' ', '_')
            # Only boost if the term looks like a single concept (1-2 words, not a complex phrase)
            if len(definition_term.split()) <= 2:
                logger.info(f"Rerank hybrid: Definition query detected, boosting chunks with clause matching: {definition_term_normalized}")
                boosted_count = 0
                for result in reranked:
                    result_clause = result.clause.lower() if result.clause else ''
                    if definition_term_normalized in result_clause:
                        # Force-boost definition chunks to ensure they're included
                        result.rerank_score = 999.0
                        boosted_count += 1
                        logger.info(f"Rerank hybrid: Force-boosted definition chunk_id={result.chunk_id[:8]}..., clause={result.clause}, score=999.0")
                
                if boosted_count > 0:
                    logger.info(f"Rerank hybrid: Force-boosted {boosted_count} definition chunks")
                else:
                    logger.info(f"Rerank hybrid: No definition chunk found for term '{definition_term_normalized}'")
        
        # Sort by rerank score
        reranked.sort(key=lambda x: x.rerank_score, reverse=True)
        
        # Log final top-k ranking
        logger.info(f"Final top-{min(len(reranked), top_k)} ranking:")
        for i, result in enumerate(reranked[:top_k]):
            logger.info(f"  {i+1}. chunk_id={result.chunk_id[:8]}..., clause={result.clause}, score={result.rerank_score:.4f}")
        
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
                content=result.content,
                original_score=result.score if hasattr(result, 'score') else result.get('score', 0.0),
                rerank_score=result.score if hasattr(result, 'score') else result.get('score', 0.0),
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
        top_k: int,
        query: str
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
            # Handle both object and dict results
            if hasattr(result, 'chunk_id'):
                content = result.content if hasattr(result, 'content') else result.get('content', '') if isinstance(result, dict) else result.get('text', '')
                clause = getattr(result, 'clause', '') or result.metadata.get('clause', '')
                fused.append(RerankedResult(
                    chunk_id=result.chunk_id,
                    source_id=result.source_id if hasattr(result, 'source_id') else result.get('source_id', ''),
                    section=result.section if hasattr(result, 'section') else result.get('section', ''),
                    article=result.article if hasattr(result, 'article') else result.get('article', ''),
                    content=content,
                    original_score=result.score if hasattr(result, 'score') else result.get('score', 0.0),
                    rerank_score=(result.score if hasattr(result, 'score') else result.get('score', 0.0)) * weight,
                    version_hash=result.version_hash if hasattr(result, 'version_hash') else result.get('version_hash', ''),
                    jurisdiction=result.jurisdiction if hasattr(result, 'jurisdiction') else result.get('jurisdiction', ''),
                    domain=result.domain if hasattr(result, 'domain') else result.get('domain', ''),
                    metadata=result.metadata if hasattr(result, 'metadata') else result.get('metadata', {}),
                    clause=clause
                ))
        
        # Apply exact-match boost for explicit clause/section references
        explicit_ref = _extract_explicit_reference(query)
        if explicit_ref:
            logger.info(f"Simple fusion: Query contains explicit reference: {explicit_ref}")
            boosted_count = 0
            for result in fused:
                result_clause = result.clause
                result_section = str(result.section)
                
                if explicit_ref in result_clause or explicit_ref == result_section:
                    # Apply 5x boost for exact match
                    result.rerank_score *= 5.0
                    boosted_count += 1
                    logger.info(f"Simple fusion: Boosted chunk_id={result.chunk_id[:8]}..., clause={result_clause}, section={result_section}, ref={explicit_ref}, new_score={result.rerank_score:.4f}")
            
            if boosted_count > 0:
                logger.info(f"Simple fusion: Applied exact-match boost to {boosted_count} results")
        
        # Apply definition chunk boost for "What is X" queries (but not "What are X" queries)
        import re
        # Only match "What is X" or "What is a X", not "What are X"
        definition_match = re.search(r'what\s+is\s+(?:a\s+)?([a-z_]+(?:\s+[a-z_]+)?)(?:\s+under|$)', query, re.IGNORECASE)
        if definition_match:
            definition_term = definition_match.group(1).strip().lower()
            # Normalize: replace spaces with underscores for clause matching
            definition_term_normalized = definition_term.replace(' ', '_')
            # Only boost if the term looks like a single concept (1-2 words, not a complex phrase)
            if len(definition_term.split()) <= 2:
                logger.info(f"Simple fusion: Definition query detected, boosting chunks with clause matching: {definition_term_normalized}")
                boosted_count = 0
                for result in fused:
                    result_clause = result.clause.lower() if result.clause else ''
                    if definition_term_normalized in result_clause:
                        # Force-boost definition chunks to ensure they're included
                        result.rerank_score = 999.0
                        boosted_count += 1
                        logger.info(f"Simple fusion: Force-boosted definition chunk_id={result.chunk_id[:8]}..., clause={result.clause}, score=999.0")
                
                if boosted_count > 0:
                    logger.info(f"Simple fusion: Force-boosted {boosted_count} definition chunks")
                else:
                    logger.info(f"Simple fusion: No definition chunk found for term '{definition_term_normalized}'")
        
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
