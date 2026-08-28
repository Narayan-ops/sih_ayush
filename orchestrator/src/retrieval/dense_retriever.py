"""
Dense Retriever using Qdrant vector database
Implements jurisdiction-separated retrieval per ADR-003
"""

import os
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue
except ImportError:
    # Placeholder for when Qdrant is installed
    QdrantClient = None

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Represents a single retrieval result"""
    chunk_id: str
    source_id: str
    section: str
    article: str
    text: str
    score: float
    version_hash: str
    jurisdiction: str
    domain: str
    metadata: Dict


class DenseRetriever:
    """
    Dense vector retrieval using Qdrant
    
    Per ADR-003: Jurisdiction separation is structural at index namespace level
    - India namespaces: in_*
    - International namespaces: intl_*
    """

    def __init__(self, qdrant_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Qdrant client
        
        Args:
            qdrant_url: Qdrant server URL (from env or parameter)
            api_key: Qdrant API key (from env or parameter)
        """
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        
        if QdrantClient is None:
            logger.warning("qdrant-client not installed. Dense retriever will be non-functional.")
            self.client = None
        else:
            self.client = QdrantClient(
                url=self.qdrant_url,
                api_key=self.api_key
            )
            logger.info(f"DenseRetriever initialized with Qdrant at {self.qdrant_url}")

    def get_collection_name(self, jurisdiction: str, domain: str) -> str:
        """
        Generate collection name with jurisdiction prefix per ADR-003
        
        Args:
            jurisdiction: 'india' or 'international'
            domain: Domain type (e.g., 'patents', 'traditional_knowledge')
            
        Returns:
            Collection name with jurisdiction prefix
        """
        if jurisdiction.lower() == 'india':
            prefix = 'in_'
        elif jurisdiction.lower() == 'international':
            prefix = 'intl_'
        else:
            raise ValueError(f"Invalid jurisdiction: {jurisdiction}. Must be 'india' or 'international'")
        
        return f"{prefix}{domain}"

    def retrieve(
        self,
        query_embedding: List[float],
        jurisdiction: str,
        domain: str,
        top_k: int = 10,
        score_threshold: float = 0.7
    ) -> List[RetrievalResult]:
        """
        Retrieve top-k similar chunks using dense vector similarity
        
        Args:
            query_embedding: Query vector from embedding model
            jurisdiction: 'india' or 'international' (enforces ADR-003)
            domain: Domain type for collection selection
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            
        Returns:
            List of retrieval results
        """
        if self.client is None:
            logger.error("Qdrant client not initialized. Cannot perform retrieval.")
            return []
        
        collection_name = self.get_collection_name(jurisdiction, domain)
        
        try:
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True
            )
            
            results = []
            for result in search_results:
                payload = result.payload
                results.append(RetrievalResult(
                    chunk_id=result.id,
                    source_id=payload.get('source_id', ''),
                    section=payload.get('section', ''),
                    article=payload.get('article', ''),
                    text=payload.get('text', ''),
                    score=result.score,
                    version_hash=payload.get('version_hash', ''),
                    jurisdiction=payload.get('jurisdiction', jurisdiction),
                    domain=payload.get('domain', domain),
                    metadata=payload.get('metadata', {})
                ))
            
            logger.info(f"Retrieved {len(results)} results from {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving from Qdrant: {e}")
            return []

    def retrieve_by_filter(
        self,
        query_embedding: List[float],
        jurisdiction: str,
        domain: str,
        filters: Dict[str, str],
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Retrieve with additional metadata filters
        
        Args:
            query_embedding: Query vector
            jurisdiction: 'india' or 'international'
            domain: Domain type
            filters: Dictionary of field=value filters
            top_k: Number of results
            
        Returns:
            Filtered retrieval results
        """
        if self.client is None:
            return []
        
        collection_name = self.get_collection_name(jurisdiction, domain)
        
        # Build Qdrant filter
        conditions = [
            FieldCondition(
                key=key,
                match=MatchValue(value=value)
            )
            for key, value in filters.items()
        ]
        
        try:
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=Filter(must=conditions),
                limit=top_k,
                with_payload=True
            )
            
            results = []
            for result in search_results:
                payload = result.payload
                results.append(RetrievalResult(
                    chunk_id=result.id,
                    source_id=payload.get('source_id', ''),
                    section=payload.get('section', ''),
                    article=payload.get('article', ''),
                    text=payload.get('text', ''),
                    score=result.score,
                    version_hash=payload.get('version_hash', ''),
                    jurisdiction=payload.get('jurisdiction', jurisdiction),
                    domain=payload.get('domain', domain),
                    metadata=payload.get('metadata', {})
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving with filters: {e}")
            return []

    def health_check(self) -> bool:
        """Check if Qdrant connection is healthy"""
        if self.client is None:
            return False
        
        try:
            collections = self.client.get_collections()
            logger.info(f"Qdrant health check passed. {len(collections.collections)} collections available.")
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
