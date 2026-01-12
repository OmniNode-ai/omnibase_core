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
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError

# Anthropic API configuration
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
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
                error_code=EnumCoreErrorCode.AUTHENTICATION_ERROR,
                context={"provider": "anthropic", "env_var": "ANTHROPIC_API_KEY"},
            )

        self.model_name = model_name
        # Anthropic uses 0.0-1.0 range, clamp if needed
        self.temperature = min(1.0, max(0.0, temperature))
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
                context={
                    "expected_provider": "anthropic",
                    "actual_provider": config.provider,
                },
            )

        api_key = os.getenv(config.api_key_env)

        return cls(
            api_key=api_key,
            model_name=config.model_name,
            temperature=config.temperature,
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
            httpx.HTTPError: If the HTTP request fails.
            ModelOnexError: If the response format is unexpected.
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
                    context={"provider": "anthropic", "model": self.model_name},
                )

            # Extract text from content blocks
            text_parts = []
            for block in content_blocks:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))

            return "".join(text_parts)

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

        except Exception:
            # boundary-ok: health check must not crash, returns False on any error
            return False


# Note: Cannot verify protocol compliance at module level without API key
# The check is done when the class is instantiated with valid credentials


__all__ = ["AnthropicLLMClient"]
