"""Durable, jurisdiction-safe chat routes for IP-SAKTI Sahayak."""

import logging
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.middleware.auth import get_current_user, verify_token
from src.services.orchestrator_client import ClassificationRequest, OrchestratorClient, QueryRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
orchestrator_client = OrchestratorClient()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    jurisdiction: Literal["india", "international", "comparative"] = "india"
    session_id: Optional[str] = None
    use_external_llm: bool = False


class ChatResponse(BaseModel):
    message: ChatMessage
    citations: List[Dict[str, Any]]
    confidence: Literal["low", "medium", "high"]
    formulation_class: Optional[str] = None
    requires_escalation: bool = False
    session_id: str


def _classification_state(response) -> Dict[str, Any]:
    return {"current_step": response.current_step, "collected_slots": response.collected_slots or {}, "status": response.status}


def _is_formulation_query(message: str) -> bool:
    """Only start the classifier for an apparent product/formulation description."""
    lower = message.lower().strip()
    if lower.startswith(("what is", "what are", "when is", "where is", "how is", "how do i register")):
        return False
    terms = ("formulation", "ingredient", "product", "medicine", "drug", "cosmetic", "aahar", "nutraceutical")
    return any(term in lower for term in terms)


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request, current_user: Optional[dict] = Depends(get_current_user)):
    """Run classification and grounded retrieval with durable session/audit state."""
    if request.use_external_llm:
        raise HTTPException(status_code=403, detail="External model use is unavailable until verified per-session consent is enabled.")
    if request.jurisdiction == "comparative":
        raise HTTPException(status_code=422, detail="Comparative mode requires two independently grounded answer sets and is not enabled in this release.")

    repository = getattr(http_request.app.state, "repository", None)
    if repository is None:
        raise HTTPException(status_code=503, detail="Persistent session and audit storage is unavailable.")

    user_id = (current_user or {}).get("user_id", "anonymous")
    session = await repository.get_session(request.session_id) if request.session_id else None
    if request.session_id and session is None:
        raise HTTPException(status_code=404, detail="Session not found or has been deleted.")
    if session and session["jurisdiction"] != request.jurisdiction:
        raise HTTPException(status_code=409, detail="A session cannot change jurisdiction. Start a new session to preserve separation.")
    if not session:
        session_id = str(await repository.create_session(user_id, request.jurisdiction))
        session = await repository.get_session(session_id)
    else:
        session_id = str(session["session_id"])

    headers = {"X-User-ID": user_id, "X-Session-ID": session_id}
    classification = session.get("classification_state")
    formulation_class = None

    if classification and classification.get("status") == "needs_clarification":
        classified = await orchestrator_client.send_classification_request(
            ClassificationRequest(user_input=request.message, existing_state=classification, session_context={"jurisdiction": request.jurisdiction}), headers
        )
        await repository.update_classification_state(session_id, _classification_state(classified))
        if classified.status == "needs_clarification":
            await repository.log_audit(session_id, request.message, [], "formulation_classifier", "self_hosted", "not_applicable", 1.0)
            return ChatResponse(message=ChatMessage(role="assistant", content=classified.clarifying_question or "Please provide the requested formulation detail."), citations=[], confidence="medium", session_id=session_id)
        formulation_class = classified.formulation_class
        message_for_query = session.get("original_query") or request.message
        await repository.update_classification_state(session_id, None)
    elif not classification and _is_formulation_query(request.message):
        classified = await orchestrator_client.send_classification_request(
            ClassificationRequest(user_input=request.message, session_context={"jurisdiction": request.jurisdiction}), headers
        )
        await repository.update_classification_state(session_id, _classification_state(classified), original_query=request.message)
        if classified.status == "needs_clarification":
            await repository.log_audit(session_id, request.message, [], "formulation_classifier", "self_hosted", "not_applicable", 1.0)
            return ChatResponse(message=ChatMessage(role="assistant", content=classified.clarifying_question or "Please provide the requested formulation detail."), citations=[], confidence="medium", session_id=session_id)
        formulation_class = classified.formulation_class
        message_for_query = request.message
        await repository.update_classification_state(session_id, None)
    else:
        message_for_query = request.message

    try:
        orchestrator_response = await orchestrator_client.send_query_request(
            QueryRequest(query=message_for_query, jurisdiction="in" if request.jurisdiction == "india" else "intl", formulation_type=formulation_class), headers
        )
    except Exception:
        logger.exception("Orchestrator request failed", extra={"session_id": session_id})
        raise HTTPException(status_code=503, detail="Grounded research service is unavailable. Check the orchestrator, retrieval stores, and self-hosted model health endpoints.")
    score = orchestrator_response.confidence_score or 0.0
    confidence: Literal["low", "medium", "high"] = "high" if score >= 0.8 else "medium" if score >= 0.5 else "low"
    chunk_ids = sorted({citation.get("chunk_id") for citation in orchestrator_response.citations if citation.get("chunk_id")})
    versions = sorted({citation.get("version_hash") for citation in orchestrator_response.citations if citation.get("version_hash")})
    await repository.log_audit(
        session_id=session_id, query=message_for_query, retrieved_chunk_ids=chunk_ids,
        model_version=orchestrator_response.model_used, provider_used=orchestrator_response.provider_used,
        corpus_version="|".join(versions) or "no_cited_corpus_version", confidence_score=score,
    )
    return ChatResponse(
        message=ChatMessage(role="assistant", content=orchestrator_response.answer), citations=orchestrator_response.citations,
        confidence=confidence, formulation_class=orchestrator_response.formulation_type,
        requires_escalation=confidence == "low", session_id=session_id,
    )


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, http_request: Request, current_user: dict = Depends(verify_token)):
    session = await http_request.app.state.repository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, http_request: Request, current_user: dict = Depends(verify_token)):
    await http_request.app.state.repository.soft_delete_session(session_id)
