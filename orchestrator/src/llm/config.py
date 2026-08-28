"""
LLM Provider Configuration
Configuration-driven provider selection per ADR-001
"""

from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv
import logging

from .provider_abstraction import LLMProviderFactory

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class LLMConfig:
    """
    LLM provider configuration
    Implements provider selection logic per ADR-001
    """
    
    def __init__(self):
        self.default_provider = os.getenv("LLM_DEFAULT_PROVIDER", "self_hosted")
        self.provider_configs = self._load_provider_configs()
    
    def _load_provider_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Load provider configurations from environment variables
        """
        configs = {
            "self_hosted": {
                "base_url": os.getenv("SELF_HOSTED_LLM_URL", "http://localhost:8000"),
                "model_name": os.getenv("SELF_HOSTED_MODEL", "llama-3.1-8b"),
                "timeout": int(os.getenv("SELF_HOSTED_TIMEOUT", "30")),
                "max_tokens": int(os.getenv("SELF_HOSTED_MAX_TOKENS", "2048")),
                "temperature": float(os.getenv("SELF_HOSTED_TEMPERATURE", "0.7")),
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model_name": os.getenv("OPENAI_MODEL", "gpt-4o"),
                "timeout": int(os.getenv("OPENAI_TIMEOUT", "30")),
                "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "4096")),
                "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            },
            "anthropic": {
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "base_url": os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
                "model_name": os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
                "timeout": int(os.getenv("ANTHROPIC_TIMEOUT", "30")),
                "max_tokens": int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096")),
                "temperature": float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7")),
            }
        }
        
        # Remove None values for optional providers
        for provider, config in configs.items():
            if provider != "self_hosted" and not config.get("api_key"):
                logger.warning(f"API key not configured for {provider}, provider will be unavailable")
                del configs[provider]
        
        return configs
    
    def get_provider(self, provider_name: Optional[str] = None) -> Any:
        """
        Get a provider instance
        Defaults to self_hosted per ADR-001
        """
        if provider_name is None:
            provider_name = self.default_provider
        
        if provider_name not in self.provider_configs:
            raise ValueError(f"Provider {provider_name} not configured")
        
        config = self.provider_configs[provider_name]
        return LLMProviderFactory.create_provider(provider_name, config)
    
    def get_available_providers(self) -> list:
        """
        Get list of available (configured) providers
        """
        return list(self.provider_configs.keys())
    
    def set_default_provider(self, provider_name: str):
        """
        Set the default provider
        Per ADR-001, this should only be self_hosted unless explicitly changed
        """
        if provider_name not in self.provider_configs:
            raise ValueError(f"Provider {provider_name} not configured")
        
        if provider_name != "self_hosted":
            logger.warning(f"Changing default provider from self_hosted to {provider_name} - this violates ADR-001 default behavior")
        
        self.default_provider = provider_name

# Global configuration instance
llm_config = LLMConfig()
