"""
Database Repository Service
Handles database operations for sessions, consent, audit, and roles
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncpg

logger = logging.getLogger(__name__)


class DatabaseRepository:
    """
    Repository for database operations
    
    Per ARCHITECTURE.md: 7-year audit retention requirement
    """

    def __init__(self, database_url: str):
        """
        Initialize database repository
        
        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
        logger.info("DatabaseRepository initialized")

    async def initialize(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(self.database_url)
        logger.info("Database connection pool created")

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    async def create_session(
        self,
        user_id: str,
        jurisdiction: str,
        provider: str = "self_hosted"
    ) -> str:
        """
        Create a new session
        
        Args:
            user_id: User identifier
            jurisdiction: Selected jurisdiction
            provider: LLM provider used
            
        Returns:
            Session ID
        """
        async with self.pool.acquire() as conn:
            session_id = await conn.fetchval(
                """
                INSERT INTO sessions (user_id, jurisdiction, provider, created_at)
                VALUES ($1, $2, $3, $4)
                RETURNING session_id
                """,
                user_id,
                jurisdiction,
                provider,
                datetime.utcnow()
            )
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a live session; deleted sessions are never returned."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT session_id, user_id, jurisdiction, provider, classification_state, original_query, created_at "
                "FROM sessions WHERE session_id = $1::uuid AND deleted_at IS NULL", session_id
            )
        return dict(row) if row else None

    async def update_classification_state(self, session_id: str, state: Optional[Dict[str, Any]], original_query: Optional[str] = None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE sessions SET classification_state=$2::jsonb, original_query=COALESCE($3, original_query), updated_at=now() "
                "WHERE session_id=$1::uuid AND deleted_at IS NULL",
                session_id, json.dumps(state) if state is not None else None, original_query
            )

    async def soft_delete_session(self, session_id: str):
        """Erases live session content while preserving required immutable audit events."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE sessions SET classification_state=NULL, original_query=NULL, deleted_at=now(), updated_at=now() "
                "WHERE session_id=$1::uuid", session_id
            )

    async def log_consent(
        self,
        session_id: str,
        provider: str,
        consented: bool,
        consent_type: str = "external_provider"
    ):
        """
        Log consent event
        
        Per ADR-001: External providers require explicit logged consent
        
        Args:
            session_id: Session identifier
            provider: Provider being consented to
            consented: Whether user consented
            consent_type: Type of consent
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO consent_log (session_id, provider, consented, consent_type, timestamp)
                VALUES ($1, $2, $3, $4, $5)
                """,
                session_id,
                provider,
                consented,
                consent_type,
                datetime.utcnow()
            )
        logger.info(f"Consent logged: session={session_id}, provider={provider}, consented={consented}")

    async def log_audit(
        self,
        session_id: str,
        query: str,
        retrieved_chunk_ids: List[str],
        model_version: str,
        provider_used: str,
        corpus_version: str,
        confidence_score: float
    ):
        """
        Log audit record
        
        Per ARCHITECTURE.md: Immutable audit trail with 7-year retention
        
        Args:
            session_id: Session identifier
            query: User query
            retrieved_chunk_ids: List of retrieved chunk IDs
            model_version: Model version used
            provider_used: Provider used
            corpus_version: Corpus version
            confidence_score: Confidence score
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_log (
                    session_id, query, retrieved_chunk_ids, model_version,
                    provider_used, corpus_version, confidence_score, timestamp
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                session_id,
                query,
                json.dumps(retrieved_chunk_ids),
                model_version,
                provider_used,
                corpus_version,
                confidence_score,
                datetime.utcnow()
            )
        logger.info(f"Audit logged: session={session_id}, provider={provider_used}")

    async def get_user_role(self, user_id: str) -> Optional[str]:
        """
        Get user role
        
        Args:
            user_id: User identifier
            
        Returns:
            User role or None
        """
        async with self.pool.acquire() as conn:
            role = await conn.fetchval(
                "SELECT role FROM user_roles WHERE user_id = $1",
                user_id
            )
        return role

    async def log_escalation(
        self,
        session_id: str,
        escalation_type: str,
        reason: str,
        facilitator_id: Optional[str] = None
    ):
        """
        Log escalation event
        
        Args:
            session_id: Session identifier
            escalation_type: Type of escalation
            reason: Reason for escalation
            facilitator_id: Assigned facilitator (if any)
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO escalation_log (session_id, escalation_type, reason, facilitator_id, timestamp)
                VALUES ($1, $2, $3, $4, $5)
                """,
                session_id,
                escalation_type,
                reason,
                facilitator_id,
                datetime.utcnow()
            )
        logger.info(f"Escalation logged: session={session_id}, type={escalation_type}")
