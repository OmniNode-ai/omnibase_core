# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Anthropic LLM client implementation using httpx.

This module provides a ProtocolLLMClient implementation for Anthropic's API.
Uses httpx for consistency with other providers.

Example:
    Basic usage::

        client = AnthropicLLMClient(api_key="sk-ant-...")
        response = await client.complete("Hello, how are you?")

    Using with environment variable::

        # Set ANTHROPIC_API_KEY environment variable
        client = AnthropicLLMClient()
        response = await client.complete(
            "Help me with a billing issue",
            system_prompt="You are a helpful assistant.",
        )
"""

from __future__ import annotations

import os

import httpx

from examples.demo.handlers.support_assistant.model_config import ModelConfig
from examples.demo.handlers.support_assistant.protocol_llm_client import (
    ProtocolLLMClient,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError

# Anthropic API configuration
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
# API version is pinned for stability - Anthropic recommends using a fixed version
# to ensure consistent behavior. Update when new features are needed.
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_TIMEOUT = 60.0


class AnthropicLLMClient:
    """LLM client for Anthropic's Claude API.

    This client uses httpx to make requests to Anthropic's messages endpoint.
    Supports Claude models including Opus, Sonnet, and Haiku.

    Attributes:
        api_key: Anthropic API key.
        model_name: Model identifier (e.g., "claude-sonnet-4-20250514").
        temperature: Sampling temperature for response generation.
        max_tokens: Maximum tokens to generate.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key.
                Defaults to ANTHROPIC_API_KEY environment variable.
            model_name: Model identifier (e.g., "claude-sonnet-4-20250514").
            temperature: Sampling temperature (0.0 to 1.0 for Anthropic).
            max_tokens: Maximum tokens to generate.
            timeout: Request timeout in seconds.

        Raises:
            ModelOnexError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ModelOnexError(
                message=(
                    "Anthropic API key is required. Set ANTHROPIC_API_KEY environment "
                    "variable or pass api_key parameter."
                ),
                error_code=EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER,
                parameter_name="api_key",
            )

        self.model_name = model_name

        # Validate temperature range (Anthropic uses 0.0-1.0 range)
        if not 0.0 <= temperature <= 1.0:
            raise ModelOnexError(
                message=f"Temperature must be between 0.0 and 1.0, got {temperature}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"temperature": temperature, "valid_range": "0.0-1.0"},
            )

        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    @classmethod
    def from_config(cls, config: ModelConfig) -> AnthropicLLMClient:
        """Create client from ModelConfig.

        Args:
            config: ModelConfig with Anthropic provider settings.

        Returns:
            Configured AnthropicLLMClient instance.

        Raises:
            ModelOnexError: If config is not for Anthropic provider.
        """
        if config.provider != "anthropic":
            raise ModelOnexError(
                message=f"Expected anthropic provider, got {config.provider}",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                expected_provider="anthropic",
                actual_provider=config.provider,
            )

        api_key = os.getenv(config.api_key_env)

        # Clamp temperature to Anthropic's valid range (0.0-1.0)
        # ModelConfig may allow higher values for other providers
        temperature = min(max(config.temperature, 0.0), 1.0)

        return cls(
            api_key=api_key,
            model_name=config.model_name,
            temperature=temperature,
            max_tokens=config.max_tokens,
        )

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Send a completion request to Anthropic.

        Uses Anthropic's messages API format which differs from OpenAI.

        Args:
            prompt: The user message/prompt.
            system_prompt: Optional system message for context.

        Returns:
            The LLM's response text.

        Raises:
            ModelOnexError: If the HTTP request fails, times out, or response
                format is unexpected. Wraps underlying httpx errors with
                appropriate error codes (SERVICE_UNAVAILABLE, NETWORK_ERROR,
                TIMEOUT_ERROR, PROCESSING_ERROR).
        """
        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        # Anthropic uses top-level system parameter, not in messages
        if system_prompt:
            payload["system"] = system_prompt

        # api_key is guaranteed non-None after __init__ validation
        assert self.api_key is not None, "api_key validated in __init__"
        headers: dict[str, str] = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    ANTHROPIC_API_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

                data = response.json()

                # Anthropic response format differs from OpenAI
                content_blocks = data.get("content", [])
                if not content_blocks:
                    raise ModelOnexError(
                        message="No content in Anthropic response",
                        error_code=EnumCoreErrorCode.PROCESSING_ERROR,
                        model=self.model_name,
                    )

                # Extract text from content blocks
                text_parts = []
                for block in content_blocks:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))

                return "".join(text_parts)

        except httpx.HTTPStatusError as e:
            # boundary-ok: wrap HTTP errors with structured error for API boundary
            raise ModelOnexError(
                message=f"Anthropic API request failed: {e.response.status_code}",
                error_code=EnumCoreErrorCode.SERVICE_UNAVAILABLE,
                status_code=e.response.status_code,
                model=self.model_name,
            ) from e
        except httpx.TimeoutException as e:
            # boundary-ok: wrap timeout errors with structured error for API boundary
            raise ModelOnexError(
                message=f"Anthropic API request timed out after {self.timeout}s",
                error_code=EnumCoreErrorCode.TIMEOUT_ERROR,
                timeout=self.timeout,
                model=self.model_name,
            ) from e
        except httpx.RequestError as e:
            # boundary-ok: wrap network errors with structured error for API boundary
            raise ModelOnexError(
                message=f"Anthropic API request failed: {e!s}",
                error_code=EnumCoreErrorCode.NETWORK_ERROR,
                model=self.model_name,
            ) from e

    async def health_check(self) -> bool:
        """Check if the Anthropic API is reachable.

        Anthropic doesn't have a dedicated health endpoint, so we check
        if the API responds with proper error for an empty request.

        Returns:
            True if the API is reachable, False otherwise.
        """
        try:
            # api_key is guaranteed non-None after __init__ validation
            assert self.api_key is not None, "api_key validated in __init__"
            headers: dict[str, str] = {
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                # Make a minimal request that will fail with 400 but prove connectivity
                response = await client.post(
                    ANTHROPIC_API_URL,
                    json={"model": self.model_name, "max_tokens": 1, "messages": []},
                    headers=headers,
                )
                # 400 means API is reachable but request is invalid (expected)
                # 401 means API is reachable but key is invalid
                return response.status_code in [200, 400, 401]

        except (httpx.HTTPStatusError, httpx.RequestError):
            # boundary-ok: health check returns False on API/network errors
            return False
        except Exception:
            # catch-all-ok: health check must not raise on unexpected errors
            return False


def _verify_protocol_compliance() -> None:
    """Verify AnthropicLLMClient implements ProtocolLLMClient.

    This function is provided for test suites to verify protocol compliance
    without import-time side effects. Tests should call this explicitly.

    Note: Cannot verify at module level without API key - the class requires
    valid credentials in __init__.

    Raises:
        AssertionError: If AnthropicLLMClient does not implement ProtocolLLMClient.
    """
    # Create a mock instance for protocol checking by bypassing __init__
    # This is safe because we're only checking protocol method signatures
    instance = object.__new__(AnthropicLLMClient)
    assert isinstance(
        instance, ProtocolLLMClient
    ), "AnthropicLLMClient must implement ProtocolLLMClient"


__all__ = ["AnthropicLLMClient", "_verify_protocol_compliance"]
