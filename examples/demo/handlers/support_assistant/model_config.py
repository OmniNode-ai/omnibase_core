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
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "ModelConfig",
    "load_config_from_contract",
    "OPENAI_CONFIG",
    "ANTHROPIC_CONFIG",
    "LOCAL_CONFIG",
]


# Pydantic models for contract provider_config validation
class _CloudProviderConfig(BaseModel):  # type: ignore[explicit-any]  # Pydantic BaseModel uses Any internally
    """Configuration for cloud LLM providers (OpenAI, Anthropic)."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    temperature: float = 0.7
    max_tokens: int = 500
    api_key_env: str


class _LocalProviderConfig(BaseModel):  # type: ignore[explicit-any]  # Pydantic BaseModel uses Any internally
    """Configuration for local LLM providers."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    temperature: float = 0.7
    max_tokens: int = 500
    endpoint_env: str = "LOCAL_LLM_ENDPOINT"
    default_endpoint: str = "http://localhost:8000"


class _ProviderConfigSection(BaseModel):  # type: ignore[explicit-any]  # Pydantic BaseModel uses Any internally
    """The provider_config section of the contract."""

    model_config = ConfigDict(extra="forbid")

    openai: _CloudProviderConfig
    anthropic: _CloudProviderConfig
    local: _LocalProviderConfig


class _ContractMetadata(BaseModel):  # type: ignore[explicit-any]  # Pydantic BaseModel uses Any internally
    """Metadata section containing provider_config."""

    model_config = ConfigDict(extra="ignore")  # Ignore other metadata fields

    provider_config: _ProviderConfigSection


class _ContractWithProviderConfig(BaseModel):  # type: ignore[explicit-any]  # Pydantic BaseModel uses Any internally
    """Partial contract model for extracting provider_config from metadata."""

    model_config = ConfigDict(extra="ignore")  # Ignore other contract fields

    metadata: _ContractMetadata


class ModelConfig(BaseModel):  # type: ignore[explicit-any]  # Pydantic BaseModel uses Any internally
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


def load_config_from_contract(
    provider: Literal["openai", "anthropic", "local"],
    contract_path: Path | None = None,
) -> ModelConfig:
    """Load ModelConfig from contract's provider_config section.

    This is the preferred way to get configuration - the contract is
    the single source of truth for all configuration values.

    Args:
        provider: The provider to load ("openai", "anthropic", or "local").
        contract_path: Path to contract YAML. Defaults to support_assistant.yaml
            in the same directory as this module.

    Returns:
        ModelConfig loaded from the contract.

    Raises:
        FileNotFoundError: If contract file not found.
        ValidationError: If contract structure is invalid.
    """
    if contract_path is None:
        contract_path = Path(__file__).parent / "support_assistant.yaml"

    # Parse YAML and validate with Pydantic model
    # Note: yaml.safe_load is allowed here per .yaml-validation-allowlist.yaml
    with open(contract_path, encoding="utf-8") as f:
        contract_data = yaml.safe_load(f)

    contract = _ContractWithProviderConfig.model_validate(contract_data)

    # Extract the provider config from metadata (Pydantic already validated it exists)
    provider_config = contract.metadata.provider_config
    if provider == "local":
        local_cfg = provider_config.local
        # Local provider uses endpoint_env and default_endpoint from contract
        endpoint_url = os.getenv(local_cfg.endpoint_env, local_cfg.default_endpoint)
        return ModelConfig(
            provider=provider,
            model_name=local_cfg.model_name,
            endpoint_url=endpoint_url,
            temperature=local_cfg.temperature,
            max_tokens=local_cfg.max_tokens,
        )
    elif provider == "anthropic":
        anthropic_cfg = provider_config.anthropic
        return ModelConfig(
            provider=provider,
            model_name=anthropic_cfg.model_name,
            temperature=anthropic_cfg.temperature,
            max_tokens=anthropic_cfg.max_tokens,
            api_key_env=anthropic_cfg.api_key_env,
        )
    else:  # openai
        openai_cfg = provider_config.openai
        return ModelConfig(
            provider=provider,
            model_name=openai_cfg.model_name,
            temperature=openai_cfg.temperature,
            max_tokens=openai_cfg.max_tokens,
            api_key_env=openai_cfg.api_key_env,
        )


# Pre-defined configurations (for backwards compatibility)
# NOTE: Prefer using load_config_from_contract() which reads from the contract.
# These static configs should match the values in support_assistant.yaml.
#
# IMPORTANT: Model identifiers follow provider naming conventions and may need
# periodic updates as providers release newer versions. Last verified: 2025-05.
#
# - OpenAI: Uses short model names (e.g., "gpt-4o", "gpt-4o-mini")
# - Anthropic: Uses versioned names with dates (e.g., "claude-sonnet-4-20250514")
# - Local: Uses model family names (e.g., "qwen2.5-coder-14b")

OPENAI_CONFIG = ModelConfig(
    provider="openai",
    model_name="gpt-4o",  # GPT-4o (omni) - multimodal model, released 2024-05
    temperature=0.7,
)

ANTHROPIC_CONFIG = ModelConfig(
    provider="anthropic",
    model_name="claude-sonnet-4-20250514",  # Claude Sonnet 4, version 2025-05-14
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
