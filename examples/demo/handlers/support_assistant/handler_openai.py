# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OpenAI LLM client implementation using httpx.

This module provides a ProtocolLLMClient implementation for OpenAI's API.
Uses httpx for consistency with other providers.

Example:
    Basic usage::

        client = OpenAILLMClient(api_key="sk-...")
        response = await client.complete("Hello, how are you?")

    Using with environment variable::

        # Set OPENAI_API_KEY environment variable
        client = OpenAILLMClient()
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
from omnibase_core.errors import EnumCoreErrorCode, ModelOnexError

# OpenAI API configuration
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4"
DEFAULT_TIMEOUT = 60.0


class OpenAILLMClient:
    """LLM client for OpenAI's API.

    This client uses httpx to make requests to OpenAI's chat completions
    endpoint. Supports all OpenAI chat models including GPT-4, GPT-4o, etc.

    Attributes:
        api_key: OpenAI API key.
        model_name: Model identifier (e.g., "gpt-4", "gpt-4o").
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
        """Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key.
                Defaults to OPENAI_API_KEY environment variable.
            model_name: Model identifier (e.g., "gpt-4").
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens to generate.
            timeout: Request timeout in seconds.

        Raises:
            ModelOnexError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ModelOnexError(
                message=(
                    "OpenAI API key is required. Set OPENAI_API_KEY "
                    "environment variable or pass api_key parameter."
                ),
                error_code=EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER,
                parameter_name="api_key",
            )

        self.model_name = model_name

        # Validate temperature range (OpenAI-compatible range is 0.0-2.0)
        if not 0.0 <= temperature <= 2.0:
            raise ModelOnexError(
                message=f"Temperature must be between 0.0 and 2.0, got {temperature}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"temperature": temperature, "valid_range": "0.0-2.0"},
            )

        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    @classmethod
    def from_config(cls, config: ModelConfig) -> OpenAILLMClient:
        """Create client from ModelConfig.

        Args:
            config: ModelConfig with OpenAI provider settings.

        Returns:
            Configured OpenAILLMClient instance.

        Raises:
            ModelOnexError: If config is not for OpenAI provider.
        """
        if config.provider != "openai":
            raise ModelOnexError(
                message=f"Expected openai provider, got {config.provider}",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                expected_provider="openai",
                actual_provider=config.provider,
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
        """Send a completion request to OpenAI.

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
        messages = []

        # OpenAI requires "JSON" to appear in system/user messages when using
        # response_format: json_object. Ensure system prompt includes JSON instruction.
        json_instruction = "You must respond with valid JSON."

        if system_prompt:
            # Append JSON instruction if not already present
            if "JSON" not in system_prompt and "json" not in system_prompt:
                system_prompt = f"{system_prompt}\n\n{json_instruction}"
            messages.append({"role": "system", "content": system_prompt})
        else:
            # No system prompt provided - add minimal JSON instruction
            messages.append({"role": "system", "content": json_instruction})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},  # Request JSON output
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    OPENAI_API_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

                data = response.json()

                choices = data.get("choices", [])
                if not choices:
                    raise ModelOnexError(
                        message="No choices in OpenAI response",
                        error_code=EnumCoreErrorCode.PROCESSING_ERROR,
                        model=self.model_name,
                    )

                message = choices[0].get("message", {})
                content: str = str(message.get("content", ""))

                return content

        except httpx.HTTPStatusError as e:
            # boundary-ok: wrap HTTP errors with structured error for API boundary
            raise ModelOnexError(
                message=f"OpenAI API request failed: {e.response.status_code}",
                error_code=EnumCoreErrorCode.SERVICE_UNAVAILABLE,
                status_code=e.response.status_code,
                model=self.model_name,
            ) from e
        except httpx.TimeoutException as e:
            # boundary-ok: wrap timeout errors with structured error for API boundary
            raise ModelOnexError(
                message=f"OpenAI API request timed out after {self.timeout}s",
                error_code=EnumCoreErrorCode.TIMEOUT_ERROR,
                timeout=self.timeout,
                model=self.model_name,
            ) from e
        except httpx.RequestError as e:
            # boundary-ok: wrap network errors with structured error for API boundary
            raise ModelOnexError(
                message=f"OpenAI API request failed: {e!s}",
                error_code=EnumCoreErrorCode.NETWORK_ERROR,
                model=self.model_name,
            ) from e

    async def health_check(self) -> bool:
        """Check if the OpenAI API is reachable.

        Makes a minimal models list request to verify connectivity.

        Returns:
            True if the API is reachable, False otherwise.
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers=headers,
                )
                return response.status_code == 200

        except (httpx.HTTPStatusError, httpx.RequestError):
            # boundary-ok: health check returns False on API/network errors
            return False
        except Exception:
            # catch-all-ok: health check must not raise on unexpected errors
            return False


def _verify_protocol_compliance() -> None:
    """Verify OpenAILLMClient implements ProtocolLLMClient.

    This function is provided for test suites to verify protocol compliance
    without import-time side effects. Tests should call this explicitly.

    Note: Full isinstance() check requires a valid API key for instantiation.
    We verify all protocol-required methods exist on the class.

    Raises:
        AssertionError: If OpenAILLMClient does not implement ProtocolLLMClient.
    """
    # Get required methods from the protocol
    protocol_methods = {
        name
        for name in dir(ProtocolLLMClient)
        if not name.startswith("_") and callable(getattr(ProtocolLLMClient, name))
    }

    # Verify all protocol methods exist on the client class
    for method_name in protocol_methods:
        assert hasattr(
            OpenAILLMClient, method_name
        ), f"OpenAILLMClient must have '{method_name}' method per ProtocolLLMClient"


__all__ = ["OpenAILLMClient", "_verify_protocol_compliance"]
