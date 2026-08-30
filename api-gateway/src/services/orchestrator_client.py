"""
Orchestrator Client Service
Handles communication between API Gateway and Orchestrator service
"""

import httpx
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str
    jurisdiction: str
    session_id: Optional[str] = None
    provider: Optional[str] = None
    provider_consent: Optional[bool] = None


class ChatResponse(BaseModel):
    """Response model from orchestrator"""
    answer: str
    citations: list
    confidence: float
    corpus_version: str
    should_abstain: bool = False
    abstention_reason: Optional[str] = None


class OrchestratorClient:
    """
    Client for communicating with the Orchestrator service
    
    Per ADR-001: Self-hosted default, external providers opt-in only
    """

    def __init__(self, orchestrator_url: str = "http://orchestrator-service:8001"):
        """
        Initialize orchestrator client
        
        Args:
            orchestrator_url: URL of the orchestrator service
        """
        self.orchestrator_url = orchestrator_url
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"OrchestratorClient initialized with URL: {orchestrator_url}")

    async def send_chat_request(
        self,
        request: ChatRequest,
        headers: Dict[str, str]
    ) -> ChatResponse:
        """
        Send chat request to orchestrator
        
        Args:
            request: Chat request with message and jurisdiction
            headers: Request headers (including auth tokens)
            
        Returns:
            Chat response with answer, citations, and confidence
        """
        try:
            response = await self.client.post(
                f"{self.orchestrator_url}/api/chat",
                json=request.dict(),
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            return ChatResponse(**data)
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error communicating with orchestrator: {e}")
            raise
        except Exception as e:
            logger.error(f"Error sending chat request: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Check orchestrator health
        
        Returns:
            Health status from orchestrator
        """
        try:
            response = await self.client.get(f"{self.orchestrator_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Orchestrator health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
