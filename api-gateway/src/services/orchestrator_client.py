"""
Orchestrator Client Service
Handles communication between API Gateway and Orchestrator service
"""

import httpx
import logging
import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """Request model matching orchestrator's QueryRequest"""
    query: str
    jurisdiction: str = "in"  # "in" for India, "intl" for International
    formulation_type: Optional[str] = None
    provider: Optional[str] = None
    include_citations: bool = True
    include_confidence: bool = True


class QueryResponse(BaseModel):
    """Response model matching orchestrator's QueryResponse"""
    answer: str
    citations: List[Dict[str, Any]]
    confidence_score: Optional[float]
    formulation_type: Optional[str]
    jurisdiction: str
    model_used: str
    provider_used: str


class ClassificationRequest(BaseModel):
    """Request model for classification endpoint"""
    user_input: str
    existing_state: Optional[Dict[str, Any]] = None
    session_context: Optional[Dict[str, Any]] = None


class ClassificationResponse(BaseModel):
    """Response model matching orchestrator's ClassificationResponse"""
    formulation_class: Optional[str]
    status: str
    current_step: Optional[str] = None
    clarifying_question: Optional[str] = None
    collected_slots: Optional[Dict[str, Any]] = None
    requires_escalation: bool
    escalation_reason: Optional[str] = None
    flags: Optional[List[str]] = None
    failed_slot: Optional[str] = None


class OrchestratorClient:
    """
    Client for communicating with the Orchestrator service
    
    Per ADR-001: Self-hosted default, external providers opt-in only
    """

    def __init__(self, orchestrator_url: Optional[str] = None):
        """
        Initialize orchestrator client
        
        Args:
            orchestrator_url: URL of the orchestrator service (defaults to ORCHESTRATOR_URL env var or http://localhost:8001)
        """
        if orchestrator_url is None:
            orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8001")
        
        self.orchestrator_url = orchestrator_url
        self.client = httpx.AsyncClient(timeout=120.0)  # Increased timeout for orchestrator processing
        logger.info(f"OrchestratorClient initialized with URL: {orchestrator_url}")
        logger.info(f"ORCHESTRATOR_URL env var: {os.getenv('ORCHESTRATOR_URL', 'NOT_SET')}")

    async def send_query_request(
        self,
        request: QueryRequest,
        headers: Dict[str, str]
    ) -> QueryResponse:
        """
        Send query request to orchestrator's /query endpoint
        
        Args:
            request: Query request with query text and jurisdiction
            headers: Request headers (including auth tokens)
            
        Returns:
            Query response with answer, citations, and confidence
        """
        try:
            response = await self.client.post(
                f"{self.orchestrator_url}/query",
                json=request.dict(),
                headers=headers,
                timeout=120.0  # Extended timeout for orchestrator processing
            )
            response.raise_for_status()
            
            data = response.json()
            return QueryResponse(**data)
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error communicating with orchestrator: {type(e).__name__}: {e}")
            logger.error(f"Request URL: {self.orchestrator_url}/query")
            logger.error(f"Request body: {request.dict()}")
            raise
        except Exception as e:
            logger.error(f"Error sending query request: {type(e).__name__}: {e}")
            logger.error(f"Request URL: {self.orchestrator_url}/query")
            logger.error(f"Request body: {request.dict()}")
            raise

    async def send_classification_request(
        self,
        request: ClassificationRequest,
        headers: Dict[str, str]
    ) -> ClassificationResponse:
        """
        Send classification request to orchestrator's /classify endpoint
        
        Args:
            request: Classification request with user input and state
            headers: Request headers (including auth tokens)
            
        Returns:
            Classification response with result or clarifying question
        """
        try:
            response = await self.client.post(
                f"{self.orchestrator_url}/classify",
                json=request.dict(),
                headers=headers,
                timeout=120.0
            )
            response.raise_for_status()
            
            data = response.json()
            return ClassificationResponse(**data)
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error communicating with orchestrator: {type(e).__name__}: {e}")
            logger.error(f"Request URL: {self.orchestrator_url}/classify")
            logger.error(f"Request body: {request.dict()}")
            raise
        except Exception as e:
            logger.error(f"Error sending classification request: {type(e).__name__}: {e}")
            logger.error(f"Request URL: {self.orchestrator_url}/classify")
            logger.error(f"Request body: {request.dict()}")
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
