"""
Universal LLM provider protocol for model-agnostic operations.

Defines the standard interface that all LLM providers must implement
for seamless provider switching and intelligent routing.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Iterator, List

from omnibase_core.model.llm.model_llm_health_response import \
    ModelLLMHealthResponse
from omnibase_core.model.llm.model_llm_request import ModelLLMRequest
from omnibase_core.model.llm.model_llm_response import ModelLLMResponse
from omnibase_core.model.llm.model_model_capabilities import \
    ModelModelCapabilities
from omnibase_core.model.llm.model_provider_config import ModelProviderConfig


class ProtocolLLMProvider(ABC):
    """
    Universal protocol for LLM providers.

    Defines the standard interface that all LLM providers
    (Ollama, OpenAI, Anthropic) must implement for seamless
    integration and intelligent routing capabilities.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name (e.g., 'ollama', 'openai', 'anthropic')."""
        pass

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Get the provider type ('local', 'external_trusted', 'external')."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is currently available and healthy."""
        pass

    @abstractmethod
    def configure(self, config: ModelProviderConfig) -> None:
        """Configure the provider with connection and authentication details."""
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models from this provider."""
        pass

    @abstractmethod
    def get_model_capabilities(self, model_name: str) -> ModelModelCapabilities:
        """Get capabilities information for a specific model."""
        pass

    @abstractmethod
    def validate_request(self, request: ModelLLMRequest) -> bool:
        """Validate that the request is compatible with this provider."""
        pass

    @abstractmethod
    def generate(self, request: ModelLLMRequest) -> ModelLLMResponse:
        """
        Generate a response using this provider.

        Args:
            request: The LLM request with prompt and parameters

        Returns:
            ModelLLMResponse: Generated response with usage metrics

        Raises:
            ProviderError: If generation fails
            ValidationError: If request is invalid
        """
        pass

    @abstractmethod
    def generate_stream(self, request: ModelLLMRequest) -> Iterator[str]:
        """
        Generate a streaming response using this provider.

        Args:
            request: The LLM request with prompt and parameters

        Yields:
            str: Streaming response chunks

        Raises:
            ProviderError: If generation fails
            ValidationError: If request is invalid
        """
        pass

    @abstractmethod
    async def generate_async(self, request: ModelLLMRequest) -> ModelLLMResponse:
        """
        Generate a response asynchronously using this provider.

        Args:
            request: The LLM request with prompt and parameters

        Returns:
            ModelLLMResponse: Generated response with usage metrics

        Raises:
            ProviderError: If generation fails
            ValidationError: If request is invalid
        """
        pass

    @abstractmethod
    def generate_stream_async(
        self, request: ModelLLMRequest
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response asynchronously using this provider.

        Args:
            request: The LLM request with prompt and parameters

        Yields:
            str: Streaming response chunks

        Raises:
            ProviderError: If generation fails
            ValidationError: If request is invalid
        """
        pass

    @abstractmethod
    def estimate_cost(self, request: ModelLLMRequest) -> float:
        """
        Estimate the cost for this request with this provider.

        Args:
            request: The LLM request to estimate cost for

        Returns:
            float: Estimated cost in USD (0.0 for local providers)
        """
        pass

    @abstractmethod
    def health_check(self) -> ModelLLMHealthResponse:
        """
        Perform a health check on the provider.

        Returns:
            ModelLLMHealthResponse: Strongly-typed health status information
        """
        pass

    def get_provider_info(self) -> dict:
        """Get comprehensive provider information."""
        return {
            "name": self.provider_name,
            "type": self.provider_type,
            "available": self.is_available,
            "available_models": self.get_available_models(),
            "health": self.health_check(),
        }

    def supports_streaming(self) -> bool:
        """Check if provider supports streaming responses."""
        try:
            # Try to call generate_stream with empty iterator check
            return hasattr(self, "generate_stream") and callable(self.generate_stream)
        except Exception:
            return False

    def supports_async(self) -> bool:
        """Check if provider supports async operations."""
        try:
            return hasattr(self, "generate_async") and callable(self.generate_async)
        except Exception:
            return False
