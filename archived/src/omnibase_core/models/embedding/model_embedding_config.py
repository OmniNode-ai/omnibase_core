"""
Complete Embedding Configuration Model.

This model defines the complete embedding configuration including
primary provider, fallback chain, and cloud fallback options.
"""

from typing import Literal

from pydantic import BaseModel, Field

from omnibase_core.models.embedding.model_embedding_provider_config import (
    ModelEmbeddingProviderConfig,
)


class ModelEmbeddingConfig(BaseModel):
    """Complete embedding configuration with fallback chain."""

    primary_provider: ModelEmbeddingProviderConfig = Field(
        description="Primary embedding provider to use",
    )

    fallback_providers: list[ModelEmbeddingProviderConfig] = Field(
        description="Ordered list of fallback providers",
        default_factory=list,
    )

    cloud_fallback_provider: Literal["gemini", "openai", "disabled"] = Field(
        description="Cloud provider to use as final fallback",
        default="gemini",
    )

    max_retry_attempts: int = Field(
        description="Maximum number of retry attempts per provider",
        default=3,
        ge=1,
    )

    connection_timeout_seconds: int = Field(
        description="Connection timeout for embedding requests",
        default=30,
        ge=1,
    )
