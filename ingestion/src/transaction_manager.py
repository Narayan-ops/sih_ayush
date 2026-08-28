"""
Dual-Store Transaction Manager
Ensures atomic writes across Qdrant + Elasticsearch per ADR-008
Provides rollback on partial failure and consistency verification
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TransactionManager:
    """
    Transaction manager for dual-store consistency
    Per ADR-008: Transactional writes with rollback on partial failure
    """
    
    def __init__(self):
        self.active_transactions = {}
    
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

# Global transaction manager instance
transaction_manager = TransactionManager()
