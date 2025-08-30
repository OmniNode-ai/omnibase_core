"""
Embedding Provider Configuration Model.

This model defines the configuration structure for embedding providers
in the conversation memory system.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ModelEmbeddingProviderConfig(BaseModel):
    """Configuration for a single embedding provider."""

    model_name: str = Field(
        description="Name of the embedding model (e.g., 'mxbai-embed-large')"
    )

    host: str = Field(
        description="Host IP address or hostname for the embedding service"
    )

    port: int = Field(
        description="Port number for the embedding service", ge=1, le=65535
    )

    dimensions: int = Field(
        description="Number of dimensions in the embedding vectors", gt=0
    )

    description: str = Field(description="Human-readable description of this provider")

    api_type: Literal["ollama", "openai", "huggingface", "gemini"] = Field(
        description="Type of API for this embedding provider"
    )

    priority: int = Field(
        description="Priority order for fallback chain (lower = higher priority)", ge=1
    )
