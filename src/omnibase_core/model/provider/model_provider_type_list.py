"""Model for managing lists of provider types."""

from typing import List

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_llm_provider import EnumLLMProvider


class ModelProviderTypeList(BaseModel):
    """
    Strongly-typed collection for managing LLM provider types.

    Replaces List[EnumLLMProvider] to comply with ONEX
    standards requiring specific typed models.
    """

    providers: List[EnumLLMProvider] = Field(
        default_factory=list, description="List of LLM provider types"
    )

    def add(self, provider_type: EnumLLMProvider) -> None:
        """Add a provider type."""
        if provider_type not in self.providers:
            self.providers.append(provider_type)

    def remove(self, provider_type: EnumLLMProvider) -> bool:
        """Remove a provider type."""
        if provider_type in self.providers:
            self.providers.remove(provider_type)
            return True
        return False

    def contains(self, provider_type: EnumLLMProvider) -> bool:
        """Check if provider type is in list."""
        return provider_type in self.providers

    def get_all(self) -> List[EnumLLMProvider]:
        """Get all provider types."""
        return self.providers.copy()

    def count(self) -> int:
        """Get number of provider types."""
        return len(self.providers)

    def clear(self) -> None:
        """Remove all provider types."""
        self.providers.clear()

    def to_list(self) -> List[EnumLLMProvider]:
        """Convert to list representation."""
        return self.providers.copy()
