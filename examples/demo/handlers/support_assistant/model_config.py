# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""ModelConfig for LLM provider configuration.

This module provides configuration for swapping between different LLM providers
(OpenAI, Anthropic, Local) in the OMN-1201 demo support assistant handler.

Example:
    Using a pre-defined configuration::

        from examples.demo.handlers.support_assistant import OPENAI_CONFIG

        # Use the pre-defined OpenAI config
        config = OPENAI_CONFIG

    Creating a custom configuration::

        from examples.demo.handlers.support_assistant import ModelConfig

        config = ModelConfig(
            provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            temperature=0.5,
            max_tokens=1000,
            api_key_env="ANTHROPIC_API_KEY",
        )
"""

import os
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "ModelConfig",
    "OPENAI_CONFIG",
    "ANTHROPIC_CONFIG",
    "LOCAL_CONFIG",
]


class ModelConfig(BaseModel):
    """Configuration for the LLM provider.

    This model allows swapping between different LLM providers (OpenAI, Anthropic,
    Local) with configurable parameters for temperature, max_tokens, and API key
    environment variable names.

    Attributes:
        provider: The LLM provider type ("openai", "anthropic", or "local").
        model_name: The name of the model to use (e.g., "gpt-4o", "claude-sonnet-4").
        endpoint_url: Custom endpoint URL for local/custom providers. Required for
            "local" provider, optional for cloud providers.
        temperature: Sampling temperature (0.0 to 2.0). Higher values make output
            more random, lower values make it more deterministic.
        max_tokens: Maximum number of tokens to generate in the response.
        api_key_env: Name of the environment variable containing the API key.

    Raises:
        ValueError: If provider is "local" but endpoint_url is not provided.
        ValueError: If temperature is outside the valid range [0.0, 2.0].
        ValueError: If max_tokens is not a positive integer.

    Example:
        Create a local provider config::

            import os

            config = ModelConfig(
                provider="local",
                model_name="qwen2.5-14b",
                endpoint_url=os.getenv("LOCAL_LLM_ENDPOINT", "http://localhost:8000"),
            )
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["openai", "anthropic", "local"] = Field(
        description="The LLM provider type"
    )
    model_name: str = Field(description="The name of the model to use")
    endpoint_url: str | None = Field(
        default=None, description="Custom endpoint URL for local/custom providers"
    )

    # Parameters
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 to 2.0)",
    )
    max_tokens: int = Field(
        default=500,
        gt=0,
        description="Maximum number of tokens to generate",
    )

    # Optional
    api_key_env: str = Field(
        default="OPENAI_API_KEY",
        description="Environment variable name for API key",
    )

    @model_validator(mode="after")
    def validate_local_provider_has_endpoint(self) -> Self:
        """Validate that local provider has an endpoint_url set.

        Local providers require a custom endpoint URL to connect to the
        local LLM server.

        Raises:
            ValueError: If provider is "local" but endpoint_url is None.
        """
        if self.provider == "local" and self.endpoint_url is None:
            raise ValueError(
                "endpoint_url is required when provider is 'local'. "
                "Local providers need a custom endpoint to connect to."
            )
        return self


# Pre-defined configurations
#
# IMPORTANT: Model identifiers follow provider naming conventions and may need
# periodic updates as providers release newer versions. Last verified: 2025-05.
#
# - OpenAI: Uses short model names (e.g., "gpt-4o", "gpt-4-turbo")
# - Anthropic: Uses versioned names with dates (e.g., "claude-sonnet-4-20250514")
# - Local: Uses model family names (e.g., "qwen2.5-coder-14b")

OPENAI_CONFIG = ModelConfig(
    provider="openai",
    model_name="gpt-4o",  # GPT-4o (omni) - multimodal model, released 2024-05
    temperature=0.7,
)

ANTHROPIC_CONFIG = ModelConfig(
    provider="anthropic",
    model_name="claude-sonnet-4-20250514",  # Claude 4 Sonnet, version 2025-05-14
    temperature=0.7,
    api_key_env="ANTHROPIC_API_KEY",
)

# Local provider configuration - uses localhost by default.
# Set LOCAL_LLM_ENDPOINT environment variable to override.
# NOTE: Do not hardcode LAN IPs; use environment variables for custom endpoints.
LOCAL_CONFIG = ModelConfig(
    provider="local",
    model_name="qwen2.5-coder-14b",  # Qwen 2.5 Coder 14B - optimized for code tasks
    endpoint_url=os.getenv("LOCAL_LLM_ENDPOINT", "http://localhost:8000"),
)
