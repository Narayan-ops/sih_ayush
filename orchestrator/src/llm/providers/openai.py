"""
OpenAI LLM Provider
Implements OpenAI API client for opt-in external provider usage
Per ADR-001: This is an opt-in provider requiring explicit user consent
"""

import httpx
import time
from typing import Optional, Dict, Any, AsyncIterator
import logging

from ..provider_abstraction import LLMProvider, LLMResponse, ModelInfo

logger = logging.getLogger(__name__)

class OpenAIProvider(LLMProvider):
    """
    OpenAI API provider
    Opt-in provider per ADR-001 requiring explicit user consent
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model_name = config.get("model_name", "gpt-4o")
        self.timeout = config.get("timeout", 30)
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.7)
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate a response from OpenAI
        """
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                        "temperature": kwargs.get("temperature", self.temperature),
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                tokens_used = result.get("usage", {}).get("total_tokens")
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                logger.info(f"OpenAI generation completed in {latency_ms}ms")
                
                return LLMResponse(
                    content=content,
                    model=self.model_name,
                    provider=self.provider_name,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    metadata={"api_base": self.base_url}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"OpenAI request failed: {e}")
            raise Exception(f"OpenAI request failed: {e}")
    
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """
        Generate a streaming response from OpenAI
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": prompt}],
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
            logger.error(f"OpenAI streaming request failed: {e}")
            raise Exception(f"OpenAI streaming request failed: {e}")
    
    def get_model_info(self) -> ModelInfo:
        """
        Get information about the OpenAI model
        """
        return ModelInfo(
            name=self.model_name,
            provider=self.provider_name,
            context_window=128000,  # GPT-4o context window
            supports_streaming=True,
            description=f"OpenAI {self.model_name} model"
        )
    
    async def health_check(self) -> bool:
        """
        Check if OpenAI API is accessible
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False
