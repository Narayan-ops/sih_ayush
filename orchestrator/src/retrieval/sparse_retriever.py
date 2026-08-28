"""
Sparse Retriever using Elasticsearch/OpenSearch
Implements keyword-based retrieval for hybrid search
"""

import os
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

try:
    from elasticsearch import Elasticsearch
except ImportError:
    # Placeholder for when Elasticsearch is installed
    Elasticsearch = None

logger = logging.getLogger(__name__)


@dataclass
class SparseResult:
    """Represents a sparse retrieval result"""
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


class SparseRetriever:
    """
    Sparse keyword retrieval using Elasticsearch
    
    Per ADR-003: Jurisdiction separation at index level
    - India indices: in_*
    - International indices: intl_*
    """

    def __init__(self, elasticsearch_url: Optional[str] = None, 
                 username: Optional[str] = None, 
                 password: Optional[str] = None):
        """
        Initialize Elasticsearch client
        
        Args:
            elasticsearch_url: Elasticsearch server URL
            username: Elasticsearch username
            password: Elasticsearch password
        """
        self.es_url = elasticsearch_url or os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        self.username = username or os.getenv("ELASTICSEARCH_USERNAME")
        self.password = password or os.getenv("ELASTICSEARCH_PASSWORD")
        
        if Elasticsearch is None:
            logger.warning("elasticsearch not installed. Sparse retriever will be non-functional.")
            self.client = None
        else:
            self.client = Elasticsearch(
                [self.es_url],
                basic_auth=(self.username, self.password) if self.username and self.password else None
            )
            logger.info(f"SparseRetriever initialized with Elasticsearch at {self.es_url}")

    def get_index_name(self, jurisdiction: str, domain: str) -> str:
        """
        Generate index name with jurisdiction prefix per ADR-003
        
        Args:
            jurisdiction: 'india' or 'international'
            domain: Domain type
            
        Returns:
            Index name with jurisdiction prefix
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
        query: str,
        jurisdiction: str,
        domain: str,
        top_k: int = 10,
        min_score: float = 0.5
    ) -> List[SparseResult]:
        """
        Retrieve top-k results using BM25 keyword search
        
        Args:
            query: Natural language query
            jurisdiction: 'india' or 'international' (enforces ADR-003)
            domain: Domain type for index selection
            top_k: Number of results to return
            min_score: Minimum relevance score
            
        Returns:
            List of sparse retrieval results
        """
        if self.client is None:
            logger.error("Elasticsearch client not initialized. Cannot perform retrieval.")
            return []
        
        index_name = self.get_index_name(jurisdiction, domain)
        
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["text", "section", "article", "metadata.*"],
                                    "type": "best_fields"
                                }
                            }
                        ]
                    }
                },
                "min_score": min_score,
                "size": top_k
            }
            
            response = self.client.search(index=index_name, body=search_body)
            
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                results.append(SparseResult(
                    chunk_id=hit['_id'],
                    source_id=source.get('source_id', ''),
                    section=source.get('section', ''),
                    article=source.get('article', ''),
                    text=source.get('text', ''),
                    score=hit['_score'],
                    version_hash=source.get('version_hash', ''),
                    jurisdiction=source.get('jurisdiction', jurisdiction),
                    domain=source.get('domain', domain),
                    metadata=source.get('metadata', {})
                ))
            
            logger.info(f"Retrieved {len(results)} results from {index_name}")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving from Elasticsearch: {e}")
            return []

    def retrieve_with_phrase(
        self,
        query: str,
        jurisdiction: str,
        domain: str,
        top_k: int = 10,
        phrase_boost: float = 2.0
    ) -> List[SparseResult]:
        """
        Retrieve with phrase matching for exact legal terminology
        
        Args:
            query: Natural language query
            jurisdiction: 'india' or 'international'
            domain: Domain type
            top_k: Number of results
            phrase_boost: Boost factor for phrase matches
            
        Returns:
            List of results with phrase emphasis
        """
        if self.client is None:
            return []
        
        index_name = self.get_index_name(jurisdiction, domain)
        
        try:
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "match_phrase": {
                                    "text": {
                                        "query": query,
                                        "boost": phrase_boost
                                    }
                                }
                            },
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["text", "section", "article"],
                                    "type": "best_fields"
                                }
                            }
                        ]
                    }
                },
                "size": top_k
            }
            
            response = self.client.search(index=index_name, body=search_body)
            
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                results.append(SparseResult(
                    chunk_id=hit['_id'],
                    source_id=source.get('source_id', ''),
                    section=source.get('section', ''),
                    article=source.get('article', ''),
                    text=source.get('text', ''),
                    score=hit['_score'],
                    version_hash=source.get('version_hash', ''),
                    jurisdiction=source.get('jurisdiction', jurisdiction),
                    domain=source.get('domain', domain),
                    metadata=source.get('metadata', {})
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving with phrase matching: {e}")
            return []

    def health_check(self) -> bool:
        """Check if Elasticsearch connection is healthy"""
        if self.client is None:
            return False
        
        try:
            health = self.client.cluster.health()
            status = health.get('status', 'unknown')
            logger.info(f"Elasticsearch health check passed. Status: {status}")
            return status in ['yellow', 'green']
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return False
