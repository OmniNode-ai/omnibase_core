"""
Protocol for LLM tool provider.

Defines the interface for providing LLM tools including model router and providers
without direct imports, enabling proper dependency injection and registry patterns.
"""

from typing import Protocol

from omnibase_core.protocol.llm.protocol_llm_provider import ProtocolLLMProvider


class ProtocolModelRouter(Protocol):
    """Protocol for model router functionality."""

    def generate(self, request):
        """Generate response using the model router."""
        ...

    def get_available_providers(self) -> list:
        """Get list of available providers."""
        ...


class ProtocolLLMToolProvider(Protocol):
    """Protocol for providing LLM tools including model router and providers."""

    def get_model_router(self) -> ProtocolModelRouter:
        """Get configured model router with registered providers."""
        ...

    def get_gemini_provider(self) -> ProtocolLLMProvider:
        """Get Gemini LLM provider."""
        ...

    def get_openai_provider(self) -> ProtocolLLMProvider:
        """Get OpenAI LLM provider."""
        ...

    def get_ollama_provider(self) -> ProtocolLLMProvider:
        """Get Ollama LLM provider."""
        ...

    def get_claude_provider(self) -> ProtocolLLMProvider:
        """Get Claude LLM provider."""
        ...
