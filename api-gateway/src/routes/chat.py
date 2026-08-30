"""
Chat Routes
Handles chat/conversation endpoints for the IP-SAKTI Sahayak interface
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
import logging

from src.middleware.auth import verify_token, get_current_user
from src.middleware.consent import require_consent, ConsentType
from src.services.orchestrator_client import OrchestratorClient, QueryRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Initialize orchestrator client
orchestrator_client = OrchestratorClient()

class ChatMessage(BaseModel):
    """Chat message model"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str  # Simplified to single message for MVP
    jurisdiction: str = "india"  # "india", "international", or "comparative"
    session_id: Optional[str] = None
    use_external_llm: bool = False

class ChatResponse(BaseModel):
    """Chat response model"""
    message: ChatMessage
    citations: List[dict]
    confidence: str  # "high", "medium", "low"
    formulation_class: Optional[str] = None
    requires_escalation: bool = False

@router.post("/")
async def chat(
    request: ChatRequest,
    current_user: Optional[dict] = Depends(get_current_user)  # Optional for dev testing
):
    """
    Main chat endpoint
    Routes to orchestrator for processing
    """
    try:
        logger.info(f"Received chat request: message='{request.message}', jurisdiction='{request.jurisdiction}'")
        
        # Check consent if external LLM is requested
        if request.use_external_llm:
            # TODO: Implement proper request object for consent check
            logger.warning(f"External LLM requested for session {request.session_id}")
        
        # Map jurisdiction from gateway format to orchestrator format
        # Gateway: "india"/"international" -> Orchestrator: "in"/"intl"
        jurisdiction_mapping = {
            "india": "in",
            "international": "intl",
            "comparative": "in"  # Default to India for comparative
        }
        orchestrator_jurisdiction = jurisdiction_mapping.get(request.jurisdiction, "in")
        
        logger.info(f"Mapped jurisdiction: {request.jurisdiction} -> {orchestrator_jurisdiction}")
        
        # Build orchestrator query request
        orchestrator_request = QueryRequest(
            query=request.message,
            jurisdiction=orchestrator_jurisdiction,
            include_citations=True,
            include_confidence=True
        )
        
        logger.info(f"Sending orchestrator request: {orchestrator_request.dict()}")
        
        # Send to orchestrator
        headers = {}
        if current_user:
            headers["X-User-ID"] = current_user.get("user_id", "unknown")
        
        orchestrator_response = await orchestrator_client.send_query_request(
            orchestrator_request,
            headers
        )
        
        logger.info(f"Received orchestrator response: confidence={orchestrator_response.confidence_score}")
        
        # Map confidence score to string
        confidence_map = {
            "high": 0.8,
            "medium": 0.5,
            "low": 0.0
        }
        confidence_str = "medium"
        if orchestrator_response.confidence_score and orchestrator_response.confidence_score >= 0.8:
            confidence_str = "high"
        elif orchestrator_response.confidence_score and orchestrator_response.confidence_score < 0.5:
            confidence_str = "low"
        
        return ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=orchestrator_response.answer,
                timestamp=None
            ),
            citations=orchestrator_response.citations,
            confidence=confidence_str,
            formulation_class=orchestrator_response.formulation_type,
            requires_escalation=False
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat request"
        )

@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(verify_token)
):
    """
    Get session history and context
    """
    # TODO: Implement session retrieval from PostgreSQL
    return {
        "session_id": session_id,
        "messages": [],
        "jurisdiction": "india",
        "formulation_class": None,
        "created_at": None
    }

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(verify_token)
):
    """
    Delete session and associated data (right to erasure)
    """
    # TODO: Implement session deletion with audit logging
    return {"status": "deleted", "session_id": session_id}
