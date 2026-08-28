"""
LLM Provider Abstraction Layer
Provider-agnostic interface for LLM calls with self-hosted and external provider support
Implements ADR-001: Self-hosted LLM as default, external providers opt-in only
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncIterator
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class LLMResponse(BaseModel):
    """Standardized LLM response"""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class ModelInfo(BaseModel):
    """Model information"""
    name: str
    provider: str
    context_window: int
    supports_streaming: bool
    description: str

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers
    All providers must implement this interface
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider_name = self.__class__.__name__.replace("Provider", "").lower()
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate a response from the LLM
        """
        pass
    
    @abstractmethod
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """
        Generate a streaming response from the LLM
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """
        Get information about the model
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and accessible
        """
        pass

class LLMProviderFactory:
    """
    Factory for creating LLM provider instances
    Implements provider selection logic per ADR-001
    """
    
    _providers = {
        "self_hosted": None,  # Will be initialized with vLLM provider
        "openai": None,      # Will be initialized with OpenAI provider
        "anthropic": None    # Will be initialized with Anthropic provider
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """Register a provider class"""
        cls._providers[name] = provider_class
    
    @classmethod
    def create_provider(cls, provider_name: str, config: Dict[str, Any]) -> LLMProvider:
        """
        Create a provider instance
        Default to self_hosted per ADR-001
        """
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        provider_class = cls._providers[provider_name]
        if provider_class is None:
            raise ValueError(f"Provider {provider_name} not registered")
        
        return provider_class(config)
    
    @classmethod
    def get_default_provider(cls) -> str:
        """
        Get the default provider name
        Per ADR-001: defaults to self_hosted
        """
        return "self_hosted"

from .providers.self_hosted import SelfHostedProvider
from .providers.openai import OpenAIProvider
from .providers.anthropic import AnthropicProvider

# Register providers
LLMProviderFactory.register_provider("self_hosted", SelfHostedProvider)
LLMProviderFactory.register_provider("openai", OpenAIProvider)
LLMProviderFactory.register_provider("anthropic", AnthropicProvider)
