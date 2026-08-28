"""
Consent Management Middleware
Handles explicit consent capture for external provider usage
DPDP Act compliance for data processing
"""

from fastapi import HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional, Literal
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class ConsentType:
    EXTERNAL_LLM = "external_llm"
    PAID_SOURCE = "paid_source"

class ConsentRequest(BaseModel):
    """Consent request model"""
    consent_type: Literal[ConsentType.EXTERNAL_LLM, ConsentType.PAID_SOURCE]
    provider_name: Optional[str] = None
    scope: str
    session_id: str

class ConsentResponse(BaseModel):
    """Consent response model"""
    consent_id: str
    granted: bool
    timestamp: datetime
    consent_type: str
    scope: str

# In-memory consent storage (replace with PostgreSQL in production)
CONSENT_STORE = {}

async def record_consent(consent_request: ConsentRequest) -> ConsentResponse:
    """
    Record user consent for external provider usage
    TODO: Store in PostgreSQL consent_logs table
    """
    consent_id = str(uuid.uuid4())
    
    consent_record = {
        "consent_id": consent_id,
        "session_id": consent_request.session_id,
        "consent_type": consent_request.consent_type,
        "provider_name": consent_request.provider_name,
        "scope": consent_request.scope,
        "timestamp": datetime.utcnow(),
        "granted": True
    }
    
    CONSENT_STORE[consent_id] = consent_record
    logger.info(f"Consent recorded: {consent_id} for session {consent_request.session_id}")
    
    return ConsentResponse(
        consent_id=consent_id,
        granted=True,
        timestamp=consent_record["timestamp"],
        consent_type=consent_request.consent_type,
        scope=consent_request.scope
    )

async def check_consent(session_id: str, consent_type: str) -> bool:
    """
    Check if consent has been granted for a specific type
    TODO: Query PostgreSQL consent_logs table
    """
    # Check if any consent exists for this session and type
    for consent_record in CONSENT_STORE.values():
        if (consent_record["session_id"] == session_id and 
            consent_record["consent_type"] == consent_type and
            consent_record["granted"]):
            return True
    
    return False

async def require_consent(request: Request, consent_type: str):
    """
    Middleware to require consent before proceeding
    Raises exception if consent not granted
    """
    session_id = request.headers.get("X-Session-ID", "")
    
    if not await check_consent(session_id, consent_type):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Consent required for {consent_type}. Please provide explicit consent."
        )
