# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Local LLM client implementation using httpx.

This module provides a ProtocolLLMClient implementation for local/self-hosted
LLM servers that expose OpenAI-compatible APIs (vLLM, Ollama, etc.).

Example:
    Using with local vLLM server::

        client = LocalLLMClient(
            endpoint_url="http://localhost:8000",
            model_name="qwen2.5-14b",
        )
        response = await client.complete("Hello, how are you?")

    Using with environment variables::

        # Set LLM_LOCAL_URL=http://your-server:8000
        client = LocalLLMClient()  # Uses env var or defaults to localhost

    Using with Ollama::

        client = LocalLLMClient(
            endpoint_url="http://localhost:11434",
            model_name="llama3",
        )
"""

from __future__ import annotations

import os

import httpx

from examples.demo.handlers.support_assistant.model_config import ModelConfig
from examples.demo.handlers.support_assistant.protocol_llm_client import \
    ProtocolLLMClient

# Default configuration - use localhost; override via LLM_LOCAL_URL or LLM_QWEN_14B_URL env vars
DEFAULT_ENDPOINT = "http://localhost:8000"
DEFAULT_MODEL = "qwen2.5-14b"
DEFAULT_TIMEOUT = 60.0


class LocalLLMClient:
    """LLM client for local/self-hosted models.

    This client connects to OpenAI-compatible API endpoints served by
    vLLM, Ollama, text-generation-inference, or similar local LLM servers.

    Attributes:
        endpoint_url: The base URL of the LLM server.
        model_name: The model identifier to use.
        temperature: Sampling temperature for response generation.
        max_tokens: Maximum tokens to generate.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        endpoint_url: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the local LLM client.

        Args:
            endpoint_url: Base URL of the LLM server.
                Defaults to environment variable LLM_LOCAL_URL or DEFAULT_ENDPOINT.
            model_name: Model identifier.
                Defaults to environment variable LLM_LOCAL_MODEL or DEFAULT_MODEL.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens to generate.
            timeout: Request timeout in seconds.
        """
        self.endpoint_url = (
            endpoint_url
            or os.getenv("LLM_LOCAL_URL")
            or os.getenv("LLM_QWEN_14B_URL")
            or DEFAULT_ENDPOINT
        )
        self.model_name = model_name or os.getenv("LLM_LOCAL_MODEL") or DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    @classmethod
    def from_config(cls, config: ModelConfig) -> LocalLLMClient:
        """Create client from ModelConfig.

        Args:
            config: ModelConfig with local provider settings.

        Returns:
            Configured LocalLLMClient instance.

        Raises:
            ValueError: If config is not for local provider.
        """
        if config.provider != "local":
            raise ValueError(f"Expected local provider, got {config.provider}")
        if config.endpoint_url is None:
            raise ValueError("endpoint_url is required for local provider")

        return cls(
            endpoint_url=config.endpoint_url,
            model_name=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Send a completion request to the local LLM server.

        Uses OpenAI-compatible chat completions API format.

        Args:
            prompt: The user message/prompt.
            system_prompt: Optional system message for context.

        Returns:
            The LLM's response text.

        Raises:
            httpx.HTTPError: If the HTTP request fails.
            ValueError: If the response format is unexpected.
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        url = f"{self.endpoint_url.rstrip('/')}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()

            # Extract response from OpenAI-compatible format
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("No choices in response")

            message = choices[0].get("message", {})
            content = message.get("content", "")

            return content

    async def health_check(self) -> bool:
        """Check if the local LLM server is healthy.

        Attempts to connect to the server's health or models endpoint.

        Returns:
            True if the server is reachable and responding, False otherwise.
        """
        try:
            # Try common health check endpoints
            endpoints = [
                f"{self.endpoint_url.rstrip('/')}/health",
                f"{self.endpoint_url.rstrip('/')}/v1/models",
            ]

            async with httpx.AsyncClient(timeout=5.0) as client:
                for endpoint in endpoints:
                    try:
                        response = await client.get(endpoint)
                        if response.status_code < 500:
                            return True
                    except httpx.HTTPError:
                        # health-check-ok: network errors for one endpoint shouldn't stop trying others
                        continue

            return False

        except (OSError, httpx.HTTPError):
            # boundary-ok: health check must return bool; network errors mean unhealthy
            return False


# Verify protocol compliance
assert isinstance(
    LocalLLMClient(), ProtocolLLMClient
), "LocalLLMClient must implement ProtocolLLMClient"


__all__ = ["LocalLLMClient"]
