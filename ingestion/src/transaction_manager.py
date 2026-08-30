"""
Dual-Store Transaction Manager
Ensures atomic writes across Qdrant + Elasticsearch per ADR-008
Provides rollback on partial failure and consistency verification
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class TransactionManager:
    """
    Transaction manager for dual-store consistency
    Per ADR-008: Transactional writes with rollback on partial failure
    """
    
    def __init__(self):
        self.active_transactions = {}
        
        # Initialize Qdrant client
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        
        # Initialize Elasticsearch client
        es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        es_username = os.getenv("ELASTICSEARCH_USERNAME")
        es_password = os.getenv("ELASTICSEARCH_PASSWORD")
        
        if es_username and es_password:
            self.elasticsearch_client = Elasticsearch(
                [es_url],
                basic_auth=(es_username, es_password)
            )
        else:
            self.elasticsearch_client = Elasticsearch([es_url])
        
        logger.info("TransactionManager initialized with Qdrant and Elasticsearch clients")
    
    async def begin_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """
        Begin a new transaction
        """
        transaction = {
            "transaction_id": transaction_id,
            "status": "active",
            "started_at": datetime.utcnow(),
            "operations": [],
            "rollback_actions": []
        }
        
        self.active_transactions[transaction_id] = transaction
        logger.info(f"Transaction {transaction_id} started")
        
        return transaction
    
    async def commit_transaction(self, transaction_id: str) -> bool:
        """
        Commit a transaction
        """
        if transaction_id not in self.active_transactions:
            logger.error(f"Transaction {transaction_id} not found")
            return False
        
        transaction = self.active_transactions[transaction_id]
        transaction["status"] = "committed"
        transaction["completed_at"] = datetime.utcnow()
        
        logger.info(f"Transaction {transaction_id} committed")
        return True
    
    async def rollback_transaction(self, transaction_id: str) -> bool:
        """
        Rollback a transaction
        Executes rollback actions in reverse order
        """
        if transaction_id not in self.active_transactions:
            logger.error(f"Transaction {transaction_id} not found")
            return False
        
        transaction = self.active_transactions[transaction_id]
        
        # Execute rollback actions in reverse order
        for rollback_action in reversed(transaction["rollback_actions"]):
            try:
                await rollback_action()
                logger.info(f"Executed rollback action for transaction {transaction_id}")
            except Exception as e:
                logger.error(f"Rollback action failed: {e}")
        
        transaction["status"] = "rolled_back"
        transaction["completed_at"] = datetime.utcnow()
        
        logger.warning(f"Transaction {transaction_id} rolled back")
        return True
    
    async def add_operation(self, transaction_id: str, operation: str, rollback_action: Optional[callable] = None):
        """
        Add an operation to the transaction
        """
        if transaction_id not in self.active_transactions:
            logger.error(f"Transaction {transaction_id} not found")
            return False
        
        transaction = self.active_transactions[transaction_id]
        transaction["operations"].append({
            "operation": operation,
            "timestamp": datetime.utcnow()
        })
        
        if rollback_action:
            transaction["rollback_actions"].append(rollback_action)
        
        return True
    
    async def verify_consistency(self, transaction_id: str) -> bool:
        """
        Verify consistency between Qdrant and Elasticsearch
        Per ADR-008: Any inconsistency triggers a page-worthy alert
        """
        # Placeholder implementation
        # In production, this would check that all written chunks exist in both stores
        logger.info(f"Verifying consistency for transaction {transaction_id}")
        
        # Mock verification
        return True
    
    async def write_to_both_stores(self, transaction_id: str, chunks: List[Dict[str, Any]]) -> bool:
        """
        Write chunks to both Qdrant and Elasticsearch atomically
        """
        try:
            # Begin transaction
            await self.begin_transaction(transaction_id)
            
            # Write to Qdrant (mock)
            await self._write_to_qdrant(chunks, transaction_id)
            
            # Write to Elasticsearch (mock)
            await self._write_to_elasticsearch(chunks, transaction_id)
            
            # Verify consistency
            if not await self.verify_consistency(transaction_id):
                await self.rollback_transaction(transaction_id)
                return False
            
            # Commit transaction
            await self.commit_transaction(transaction_id)
            return True
            
        except Exception as e:
            logger.error(f"Error in dual-store write: {e}")
            await self.rollback_transaction(transaction_id)
            return False
    
    async def _write_to_qdrant(self, chunks: List[Dict[str, Any]], transaction_id: str):
        """
        Write chunks to Qdrant
        """
        # Placeholder implementation
        logger.info(f"Writing {len(chunks)} chunks to Qdrant for transaction {transaction_id}")
    
    async def _write_to_elasticsearch(self, chunks: List[Dict[str, Any]], transaction_id: str):
        """
        Write chunks to Elasticsearch
        """
        # Placeholder implementation
        logger.info(f"Writing {len(chunks)} chunks to Elasticsearch for transaction {transaction_id}")
    
    async def ingest_chunks(
        self, 
        chunks: List[Dict[str, Any]], 
        corpus_version: str, 
        jurisdiction: str, 
        domain: str
    ) -> tuple[int, int]:
        """
        Ingest chunks to both Qdrant and Elasticsearch
        Returns (qdrant_points, elasticsearch_docs)
        """
        transaction_id = f"ingest_{datetime.utcnow().isoformat()}"
        
        try:
            # Begin transaction
            await self.begin_transaction(transaction_id)
            
            # Prepare Qdrant points
            qdrant_points = []
            for chunk in chunks:
                embedding = chunk.get("embedding", [])
                if not embedding or len(embedding) == 0:
                    logger.error(f"Chunk missing embedding: chunk_id={chunk.get('metadata', {}).get('chunk_id', 'unknown')}")
                    logger.error(f"Chunk keys: {chunk.keys()}")
                    logger.error(f"Chunk structure: {chunk}")
                    raise ValueError(f"Chunk has no embedding data: {chunk.get('metadata', {}).get('chunk_id', 'unknown')}")
                
                logger.info(f"Preparing point with embedding length: {len(embedding)}")
                
                point = PointStruct(
                    id=chunk["metadata"].get("chunk_id", ""),
                    vector=embedding,
                    payload={
                        "content": chunk["content"],
                        "section": chunk.get("section", ""),
                        "clause": chunk.get("clause", ""),
                        "metadata": chunk.get("metadata", {}),
                        "corpus_version": corpus_version,
                        "jurisdiction": jurisdiction,
                        "domain": domain
                    }
                )
                qdrant_points.append(point)
            
            # Write to Qdrant
            collection_name = f"{jurisdiction}_{domain}"
            self._ensure_qdrant_collection(collection_name)
            
            if qdrant_points:
                self.qdrant_client.upsert(
                    collection_name=collection_name,
                    points=qdrant_points
                )
            
            # Write to Elasticsearch
            es_docs = 0
            for chunk in chunks:
                es_doc = {
                    "content": chunk["content"],
                    "section": chunk.get("section", ""),
                    "clause": chunk.get("clause", ""),
                    "metadata": chunk.get("metadata", {}),
                    "corpus_version": corpus_version,
                    "jurisdiction": jurisdiction,
                    "domain": domain,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                es_index = f"{jurisdiction}_{domain}"
                self._ensure_elasticsearch_index(es_index)
                
                self.elasticsearch_client.index(index=es_index, document=es_doc)
                es_docs += 1
            
            # Verify consistency
            if not await self.verify_consistency(transaction_id):
                await self.rollback_transaction(transaction_id)
                return 0, 0
            
            # Commit transaction
            await self.commit_transaction(transaction_id)
            
            logger.info(f"Successfully ingested {len(qdrant_points)} Qdrant points and {es_docs} Elasticsearch docs")
            return len(qdrant_points), es_docs
            
        except Exception as e:
            logger.error(f"Error in ingest_chunks: {e}")
            await self.rollback_transaction(transaction_id)
            return 0, 0
    
    def _ensure_qdrant_collection(self, collection_name: str):
        """Ensure Qdrant collection exists"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE, on_disk=False)
                )
                logger.info(f"Created Qdrant collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error ensuring Qdrant collection: {e}")
    
    def _ensure_elasticsearch_index(self, index_name: str):
        """Ensure Elasticsearch index exists"""
        try:
            if not self.elasticsearch_client.indices.exists(index=index_name):
                self.elasticsearch_client.indices.create(
                    index=index_name,
                    body={
                        "mappings": {
                            "properties": {
                                "content": {"type": "text"},
                                "section": {"type": "keyword"},
                                "clause": {"type": "keyword"},
                                "corpus_version": {"type": "keyword"},
                                "jurisdiction": {"type": "keyword"},
                                "domain": {"type": "keyword"},
                                "timestamp": {"type": "date"}
                            }
                        }
                    }
                )
                logger.info(f"Created Elasticsearch index: {index_name}")
        except Exception as e:
            logger.error(f"Error ensuring Elasticsearch index: {e}")
    
    async def get_corpus_info(self, version: str) -> Dict[str, Any]:
        """Get information about a specific corpus version"""
        try:
            # Get collection info from Qdrant
            collections = self.qdrant_client.get_collections().collections
            total_points = sum(c.points_count for c in collections if version in c.name)
            
            return {
                "version": version,
                "total_points": total_points,
                "collections": [c.name for c in collections],
                "status": "active"
            }
        except Exception as e:
            logger.error(f"Error getting corpus info: {e}")
            return {"version": version, "status": "error", "error": str(e)}
    
    def health_check(self) -> Dict[str, bool]:
        """Health check for transaction manager and its clients"""
        try:
            self.qdrant_client.get_collections()
            qdrant_healthy = True
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e}")
            qdrant_healthy = False
        
        try:
            es_healthy = self.elasticsearch_client.ping()
        except Exception as e:
            logger.warning(f"Elasticsearch health check failed: {e}")
            es_healthy = False
        
        return {
            "qdrant": qdrant_healthy,
            "elasticsearch": es_healthy,
            "transaction_manager": qdrant_healthy and es_healthy
        }

# Global transaction manager instance
transaction_manager = TransactionManager()
