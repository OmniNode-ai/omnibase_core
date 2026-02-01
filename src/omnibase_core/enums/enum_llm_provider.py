"""
Enum for LLM provider types.

Defines supported LLM providers for agent system.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumLlmProvider(StrValueHelper, str, Enum):
    """Supported LLM providers for agents."""

    CLAUDE = "claude"
    OLLAMA = "ollama"
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    LITELLM = "litellm"

    def is_local(self) -> bool:
        """Check if this is a local provider."""
        return self in {self.OLLAMA, self.LOCAL, self.LITELLM}

    def requires_api_key(self) -> bool:
        """Check if this provider requires an API key."""
        return self in {self.CLAUDE, self.OPENAI, self.GEMINI, self.ANTHROPIC}


__all__ = ["EnumLlmProvider"]
