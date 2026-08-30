"""
Self-Hosted LLM Provider
Implements vLLM/inference server client for self-hosted models
Per ADR-001: This is the default provider for data sovereignty compliance
"""

import httpx
import time
from typing import Optional, Dict, Any, AsyncIterator
import logging

from ..provider_abstraction import LLMProvider, LLMResponse, ModelInfo

logger = logging.getLogger(__name__)

class SelfHostedProvider(LLMProvider):
    """
    Self-hosted LLM provider using vLLM inference server
    Default provider per ADR-001 for data sovereignty compliance
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:8000")
        self.model_name = config.get("model_name", "llama3.1:8b")
        self.timeout = config.get("timeout", 30)
        self.max_tokens = config.get("max_tokens", 2048)
        self.temperature = config.get("temperature", 0.7)
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate a response from the self-hosted LLM
        """
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/completions",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                        "temperature": kwargs.get("temperature", self.temperature),
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["text"]
                tokens_used = result.get("usage", {}).get("total_tokens")
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                logger.info(f"Self-hosted LLM generation completed in {latency_ms}ms")
                
                return LLMResponse(
                    content=content,
                    model=self.model_name,
                    provider=self.provider_name,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    metadata={"endpoint": self.base_url}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"Self-hosted LLM request failed: {e}")
            raise Exception(f"Self-hosted LLM request failed: {e}")
    
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """
        Generate a streaming response from the self-hosted LLM
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/completions",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                        "temperature": kwargs.get("temperature", self.temperature),
                        "stream": True
                    }
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            if data == "[DONE]":
                                break
                            # Parse SSE data and yield content
                            # This is a simplified implementation
                            yield data
                            
        except httpx.HTTPError as e:
            logger.error(f"Self-hosted LLM streaming request failed: {e}")
            raise Exception(f"Self-hosted LLM streaming request failed: {e}")
    
    def get_model_info(self) -> ModelInfo:
        """
        Get information about the self-hosted model
        """
        return ModelInfo(
            name=self.model_name,
            provider=self.provider_name,
            context_window=8192,  # Typical for 8B models
            supports_streaming=True,
            description=f"Self-hosted {self.model_name} model via vLLM"
        )
    
    async def health_check(self) -> bool:
        """
        Check if the self-hosted LLM server is healthy
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Self-hosted LLM health check failed: {e}")
            return False
