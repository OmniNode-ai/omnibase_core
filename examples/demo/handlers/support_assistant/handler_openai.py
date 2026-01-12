# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
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
                message="OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter.",
                error_code=EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER,
                parameter_name="api_key",
            )

        self.model_name = model_name
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
            httpx.HTTPError: If the HTTP request fails.
            ModelOnexError: If the response format is unexpected.
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
            content = message.get("content", "")

            return content

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

        except Exception:  # catch-all-ok: health check must not raise, returns False on any error
            return False


# Note: Cannot verify protocol compliance at module level without API key
# The check is done when the class is instantiated with valid credentials


__all__ = ["OpenAILLMClient"]
