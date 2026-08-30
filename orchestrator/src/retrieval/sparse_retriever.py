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
@dataclass
class SparseResult:
    """Represents a sparse retrieval result"""
    chunk_id: str
    source_id: str
    section: str
    article: str
    content: str  # Changed from text to content to match ingestion
    score: float
    version_hash: str
    jurisdiction: str
    domain: str
    metadata: Dict
    clause: str = ""  # Added clause field for logging


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
            # Extract multi-word phrases for exact phrase matching (2-4 words)
            import re
            phrases = re.findall(r'"([^"]+)"', query)  # Extract quoted phrases
            words = query.replace('"', '').split()
            
            # Extract n-grams (2, 3, and 4 word sequences)
            for n in [2, 3, 4]:
                for i in range(len(words) - n + 1):
                    phrase = ' '.join(words[i:i+n])
                    if len(phrase) > 5:  # Only consider phrases longer than 5 chars
                        phrases.append(phrase)
            
            # For definition queries ("What is X"), extract the term being defined
            # and try to match it in "X means" patterns used in legal definitions
            definition_match = re.match(r'what\s+is\s+(?:a|an|the\s+)?(.+?)(?:\s+under\s+.+)?$', query, re.IGNORECASE)
            if definition_match:
                term = definition_match.group(1).strip()
                if len(term) > 3:  # Ignore very short terms
                    # Try to match "term means" patterns common in legal definitions
                    phrases.append(f"{term} means")
                    phrases.append(f"{term}, in relation to")
                    phrases.append(f"{term}, in relation to goods, means")
            
            # Remove standalone 4-digit years from query to reduce their score contribution
            # Years like 1999, 2001, 2024 are near-universal in legal documents and shouldn't act as rare, high-signal terms
            query_without_years = re.sub(r'\b(19|20)\d{2}\b', '', query)
            query_without_years = ' '.join(query_without_years.split())  # Clean up extra spaces
            
            # Build query with phrase boosting
            bool_query = {
                "should": [
                    {
                        "multi_match": {
                            "query": query_without_years,
                            "fields": ["content", "clause^3", "section^2"],
                            "type": "best_fields"
                        }
                    }
                ]
            }
            
            # Add exact phrase matches with high boost
            for phrase in set(phrases):  # Deduplicate phrases
                bool_query["should"].append({
                    "match_phrase": {
                        "content": {
                            "query": phrase,
                            "boost": 5.0  # High boost for exact phrase matches
                        }
                    }
                })
            
            search_body = {
                "query": {
                    "bool": bool_query
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
                    content=source.get('content', ''),
                    score=hit['_score'],
                    version_hash=source.get('version_hash', ''),
                    jurisdiction=source.get('jurisdiction', jurisdiction),
                    domain=source.get('domain', domain),
                    metadata=source.get('metadata', {}),
                    clause=source.get('clause', '')
                ))
                logger.info(f"Sparse: chunk_id={hit['_id'][:8]}..., clause={source.get('clause', 'N/A')}, score={hit['_score']:.4f}")
            
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
                    content=source.get('content', ''),
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
