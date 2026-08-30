"""
Hybrid Retriever combining dense + sparse retrieval with cross-encoder reranking
Main retrieval orchestration per ARCHITECTURE.md
"""

import logging
from typing import List, Optional, Dict
from .dense_retriever import DenseRetriever
from .sparse_retriever import SparseRetriever, SparseResult
from .reranker import CrossEncoderReranker, RerankedResult

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid retrieval combining dense vector search and sparse keyword search
    with cross-encoder reranking for optimal precision
    
    Per ADR-003: Enforces jurisdiction separation at retrieval level
    """

    def __init__(
        self,
        dense_retriever: Optional[DenseRetriever] = None,
        sparse_retriever: Optional[SparseRetriever] = None,
        reranker: Optional[CrossEncoderReranker] = None
    ):
        """
        Initialize hybrid retriever with components
        
        Args:
            dense_retriever: Dense vector retriever (Qdrant)
            sparse_retriever: Sparse keyword retriever (Elasticsearch)
            reranker: Cross-encoder reranker
        """
        self.dense_retriever = dense_retriever or DenseRetriever()
        self.sparse_retriever = sparse_retriever or SparseRetriever()
        self.reranker = reranker or CrossEncoderReranker()
        
        logger.info("HybridRetriever initialized")

    def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        jurisdiction: str,
        domain: str,
        top_k: int = 10,
        dense_k: int = 20,
        sparse_k: int = 20,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
        enable_rerank: bool = True
    ) -> List[RerankedResult]:
        """
        Perform hybrid retrieval with optional reranking
        
        Args:
            query: Natural language query text
            query_embedding: Query vector for dense retrieval
            jurisdiction: 'india' or 'international' (enforces ADR-003)
            domain: Domain type (patents, traditional_knowledge, etc.)
            top_k: Final number of results to return
            dense_k: Number of dense results to retrieve before fusion
            sparse_k: Number of sparse results to retrieve before fusion
            dense_weight: Weight for dense results in fusion
            sparse_weight: Weight for sparse results in fusion
            enable_rerank: Whether to apply cross-encoder reranking
            
        Returns:
            Reranked and fused retrieval results
        """
        # Enforce jurisdiction separation per ADR-003
        if jurisdiction not in ['india', 'international']:
            raise ValueError(
                f"Invalid jurisdiction: {jurisdiction}. "
                "Must be 'india' or 'international' per ADR-003"
            )
        
        logger.info(
            f"Hybrid retrieval: jurisdiction={jurisdiction}, domain={domain}, "
            f"top_k={top_k}, rerank={enable_rerank}"
        )
        
        # Parallel dense and sparse retrieval
        dense_results = self.dense_retriever.retrieve(
            query_embedding=query_embedding,
            jurisdiction=jurisdiction,
            domain=domain,
            top_k=dense_k
        )
        
        sparse_results = self.sparse_retriever.retrieve(
            query=query,
            jurisdiction=jurisdiction,
            domain=domain,
            top_k=sparse_k
        )
        
        logger.info(
            f"Retrieved {len(dense_results)} dense, {len(sparse_results)} sparse results"
        )
        
        # Rerank and fuse
        if enable_rerank and self.reranker.model is not None:
            final_results = self.reranker.rerank_hybrid(
                query=query,
                dense_results=dense_results,
                sparse_results=sparse_results,
                dense_weight=dense_weight,
                sparse_weight=sparse_weight,
                top_k=top_k
            )
        else:
            # Simple fusion without reranking
            final_results = self.reranker._simple_fusion(
                dense_results,
                sparse_results,
                dense_weight,
                sparse_weight,
                top_k,
                query
            )
        
        logger.info(f"Final results after fusion: {len(final_results)}")
        return final_results

    def retrieve_comparative(
        self,
        query: str,
        query_embedding: List[float],
        domain: str,
        top_k: int = 10,
        enable_rerank: bool = True
    ) -> Dict[str, List[RerankedResult]]:
        """
        Retrieve from both jurisdictions for comparative mode
        
        Per ADR-003: Comparative mode is explicit opt-in only, rendered as two columns
        
        Args:
            query: Natural language query
            query_embedding: Query vector
            domain: Domain type
            top_k: Results per jurisdiction
            enable_rerank: Whether to apply reranking
            
        Returns:
            Dictionary with 'india' and 'international' result lists
        """
        logger.info(f"Comparative retrieval for domain={domain}")
        
        india_results = self.retrieve(
            query=query,
            query_embedding=query_embedding,
            jurisdiction='india',
            domain=domain,
            top_k=top_k,
            enable_rerank=enable_rerank
        )
        
        international_results = self.retrieve(
            query=query,
            query_embedding=query_embedding,
            jurisdiction='international',
            domain=domain,
            top_k=top_k,
            enable_rerank=enable_rerank
        )
        
        return {
            'india': india_results,
            'international': international_results
        }

    def retrieve_with_filters(
        self,
        query: str,
        query_embedding: List[float],
        jurisdiction: str,
        domain: str,
        filters: Dict[str, str],
        top_k: int = 10,
        enable_rerank: bool = True
    ) -> List[RerankedResult]:
        """
        Retrieve with metadata filters (e.g., specific statutes, sections)
        
        Args:
            query: Natural language query
            query_embedding: Query vector
            jurisdiction: 'india' or 'international'
            domain: Domain type
            filters: Metadata filters (e.g., {'statute': 'Patents Act'})
            top_k: Number of results
            enable_rerank: Whether to apply reranking
            
        Returns:
            Filtered and reranked results
        """
        logger.info(f"Filtered retrieval: jurisdiction={jurisdiction}, filters={filters}")
        
        # Use dense retriever with filters
        dense_results = self.dense_retriever.retrieve_by_filter(
            query_embedding=query_embedding,
            jurisdiction=jurisdiction,
            domain=domain,
            filters=filters,
            top_k=top_k * 2  # Retrieve more for reranking
        )
        
        # Sparse retrieval without additional filters (ES handles this in query)
        sparse_results = self.sparse_retriever.retrieve(
            query=query,
            jurisdiction=jurisdiction,
            domain=domain,
            top_k=top_k * 2
        )
        
        # Rerank if enabled
        if enable_rerank and self.reranker.model is not None:
            final_results = self.reranker.rerank_hybrid(
                query=query,
                dense_results=dense_results,
                sparse_results=sparse_results,
                dense_weight=0.6,
                sparse_weight=0.4,
                top_k=top_k
            )
        else:
            final_results = self.reranker._simple_fusion(
                dense_results,
                sparse_results,
                0.6,
                0.4,
                top_k,
                query
            )
        
        return final_results

    def health_check(self) -> Dict[str, bool]:
        """
        Health check for all retrieval components
        
        Returns:
            Dictionary with health status of each component
        """
        return {
            'dense_retriever': self.dense_retriever.health_check(),
            'sparse_retriever': self.sparse_retriever.health_check(),
            'reranker': self.reranker.health_check()
        }
