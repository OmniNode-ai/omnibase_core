"""Model for managing LLM providers."""

from typing import Dict

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_llm_provider import EnumLLMProvider
from omnibase_core.protocol.llm.protocol_llm_provider import \
    ProtocolLLMProvider


class ModelProviderMap(BaseModel):
    """
    Strongly-typed mapping for LLM provider management.

    Replaces Dict[EnumLLMProvider, ProtocolLLMProvider] to comply with ONEX
    standards requiring specific typed models.
    """

    providers: Dict[EnumLLMProvider, ProtocolLLMProvider] = Field(
        default_factory=dict, description="Map of provider types to provider instances"
    )

    class Config:
        # Allow ProtocolLLMProvider objects in Pydantic model
        arbitrary_types_allowed = True

    def add_provider(
        self, provider_type: EnumLLMProvider, provider: ProtocolLLMProvider
    ) -> None:
        """Add an LLM provider."""
        self.providers[provider_type] = provider

    def get_provider(self, provider_type: EnumLLMProvider) -> ProtocolLLMProvider:
        """Get provider by type."""
        return self.providers.get(provider_type)

    def remove_provider(self, provider_type: EnumLLMProvider) -> bool:
        """Remove a provider."""
        if provider_type in self.providers:
            del self.providers[provider_type]
            return True
        return False

    def has_provider(self, provider_type: EnumLLMProvider) -> bool:
        """Check if provider exists."""
        return provider_type in self.providers

    def get_all_providers(self) -> Dict[EnumLLMProvider, ProtocolLLMProvider]:
        """Get all providers."""
        return self.providers

    def get_provider_types(self) -> list:
        """Get list of available provider types."""
        return list(self.providers.keys())

    def count(self) -> int:
        """Get total number of providers."""
        return len(self.providers)

    def clear(self) -> None:
        """Remove all providers."""
        self.providers.clear()
