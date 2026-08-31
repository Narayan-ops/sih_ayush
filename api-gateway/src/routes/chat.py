"""
Chat Routes
Handles chat/conversation endpoints for the IP-SAKTI Sahayak interface
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import time
import uuid

from src.middleware.auth import verify_token, get_current_user
from src.middleware.consent import require_consent, ConsentType
from src.services.orchestrator_client import OrchestratorClient, QueryRequest, ClassificationRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Initialize orchestrator client
orchestrator_client = OrchestratorClient()

# Simple in-memory session store
# TODO: Replace with Redis/PostgreSQL for production
classification_sessions: Dict[str, Dict] = {}

def create_session(session_id: str) -> Dict:
    return {
        "session_id": session_id,
        "created_at": time.time(),
        "classification_state": None,
        "messages": [],
        "original_query": None  # Store original user query for after classification
    }

def get_session_state(session_id: str) -> Optional[Dict]:
    return classification_sessions.get(session_id)

def update_session_state(session_id: str, state: Dict):
    if session_id in classification_sessions:
        classification_sessions[session_id]["classification_state"] = state
        logger.info(f"Updated session {session_id} with state: {state}")

def _is_formulation_query(message: str) -> bool:
    """
    Skip classification for clearly non-formulation queries
    KNOWN-CRUDE HEURISTIC: This will misclassify some formulation questions phrased as "what is"
    This is intentional debt, not something to perfect right now.
    """
    lower_msg = message.lower()
    
    # Skip definition questions
    if lower_msg.startswith("what is") or lower_msg.startswith("what are"):
        return False
    
    # Skip "how to" questions that aren't about formulation
    if lower_msg.startswith("how to") and "register" in lower_msg:
        return False
    
    # Otherwise, assume it might be a formulation description
    return True

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
    classification_state: Optional[Dict[str, Any]] = None  # For multi-turn classification
    
    class Config:
        arbitrary_types_allowed = True

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
        logger.info(f"Received chat request: message='{request.message}', jurisdiction='{request.jurisdiction}', session_id='{request.session_id}'")
        
        # Check consent if external LLM is requested
        if request.use_external_llm:
            # TODO: Implement proper request object for consent check
            logger.warning(f"External LLM requested for session {request.session_id}")
        
        # Generate session_id if not provided
        if not request.session_id:
            request.session_id = str(uuid.uuid4())
        
        # Get or create session
        session = get_session_state(request.session_id)
        if not session:
            session = create_session(request.session_id)
            classification_sessions[request.session_id] = session
        
        # Check if classification is in progress
        classification_state = session.get("classification_state")
        
        # Initialize formulation_class to None unless classification completes
        formulation_class = None
        
        if classification_state and classification_state.get("status") == "needs_clarification":
            # User is answering a clarifying question - resume classification
            logger.info(f"Resuming classification with user answer: '{request.message}'")
            
            # Build headers for orchestrator calls
            orchestrator_headers = {}
            if current_user:
                orchestrator_headers["X-User-ID"] = current_user.get("user_id", "unknown")
            
            # Call orchestrator's formulation classifier with existing state
            classification_request = ClassificationRequest(
                user_input=request.message,
                existing_state=classification_state,
                session_context={"jurisdiction": request.jurisdiction}
            )
            
            classification_response = await orchestrator_client.send_classification_request(
                classification_request,
                orchestrator_headers
            )
            
            logger.info(f"Classification response: status={classification_response.status}, formulation_class={classification_response.formulation_class}")
            
            # Update session state with new classification state
            new_classification_state = {
                "current_step": classification_response.current_step,
                "collected_slots": classification_response.collected_slots,
                "status": classification_response.status
            }
            update_session_state(request.session_id, new_classification_state)
            
            # If still needs clarification, return the question
            if classification_response.status == "needs_clarification":
                return ChatResponse(
                    message=ChatMessage(
                        role="assistant",
                        content=classification_response.clarifying_question,
                        timestamp=None
                    ),
                    citations=[],
                    confidence="medium",
                    formulation_class=None,
                    requires_escalation=False
                )
            
            # Classification complete - proceed to orchestrator query with formulation_class
            formulation_class = classification_response.formulation_class
            logger.info(f"Classification completed with formulation_class: {formulation_class}")
            
            # Use original query for orchestrator, not the classification answer
            original_query = classification_sessions[request.session_id].get("original_query", request.message)
            if original_query:
                logger.info(f"Using original query for orchestrator: {original_query}")
                request.message = original_query
        
        # If no classification in progress, check if this is a formulation query
        elif not classification_state and _is_formulation_query(request.message) and formulation_class is None:
            logger.info("Query appears to be formulation-related, starting classification")
            
            # Store original query for later use after classification completes
            classification_sessions[request.session_id]["original_query"] = request.message
            
            # Build headers for orchestrator calls
            orchestrator_headers = {}
            if current_user:
                orchestrator_headers["X-User-ID"] = current_user.get("user_id", "unknown")
            
            # Call orchestrator's formulation classifier
            classification_request = ClassificationRequest(
                user_input=request.message,
                existing_state=None,
                session_context={"jurisdiction": request.jurisdiction}
            )
            
            classification_response = await orchestrator_client.send_classification_request(
                classification_request,
                orchestrator_headers
            )
            
            logger.info(f"Classification response: status={classification_response.status}, formulation_class={classification_response.formulation_class}")
            
            # Update session state with new classification state
            new_classification_state = {
                "current_step": classification_response.current_step,
                "collected_slots": classification_response.collected_slots,
                "status": classification_response.status
            }
            update_session_state(request.session_id, new_classification_state)
            
            # If needs clarification, return the question
            if classification_response.status == "needs_clarification":
                return ChatResponse(
                    message=ChatMessage(
                        role="assistant",
                        content=classification_response.clarifying_question,
                        timestamp=None
                    ),
                    citations=[],
                    confidence="medium",
                    formulation_class=None,
                    requires_escalation=False
                )
            
            # Classification complete - use the result
            formulation_class = classification_response.formulation_class
            logger.info(f"Classification completed with formulation_class: {formulation_class}")
            
            # Use original query for orchestrator, not the classification answer
            original_query = classification_sessions[request.session_id].get("original_query", request.message)
            if original_query:
                logger.info(f"Using original query for orchestrator: {original_query}")
                request.message = original_query
        
        # Map jurisdiction from gateway format to orchestrator format
        # Gateway: "india"/"international" -> Orchestrator: "in"/"intl"
        jurisdiction_mapping = {
            "india": "in",
            "international": "intl",
            "comparative": "in"  # Default to India for comparative
        }
        orchestrator_jurisdiction = jurisdiction_mapping.get(request.jurisdiction, "in")
        
        logger.info(f"Mapped jurisdiction: {request.jurisdiction} -> {orchestrator_jurisdiction}")
        
        # Build headers for orchestrator calls
        orchestrator_headers = {}
        if current_user:
            orchestrator_headers["X-User-ID"] = current_user.get("user_id", "unknown")
        
        # Build orchestrator query request
        orchestrator_request = QueryRequest(
            query=request.message,
            jurisdiction=orchestrator_jurisdiction,
            formulation_type=formulation_class,
            include_citations=True,
            include_confidence=True
        )
        
        logger.info(f"Sending orchestrator request: {orchestrator_request.dict()}")
        
        # Send to orchestrator
        orchestrator_response = await orchestrator_client.send_query_request(
            orchestrator_request,
            orchestrator_headers
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
