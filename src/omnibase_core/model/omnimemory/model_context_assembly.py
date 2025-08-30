"""
Context assembly models for OmniMemory system.

Represents context assembly metadata and configuration.
"""

from pydantic import BaseModel, Field


class ModelContextMetadata(BaseModel):
    """Metadata for context assembly operations."""

    priority: int = Field(default=0, description="Priority level for content ordering")
    source: str | None = Field(None, description="Source of the context content")
    category: str | None = Field(None, description="Category of content")
    token_count: int = Field(default=0, description="Estimated token count")
    is_essential: bool = Field(
        default=False,
        description="Whether content is essential",
    )
    compression_ratio: float = Field(
        default=1.0,
        description="Applied compression ratio",
    )


class ModelAssemblyConfiguration(BaseModel):
    """Configuration for context assembly operations."""

    max_tokens: int = Field(default=2000, description="Maximum token limit")
    compression_threshold: float = Field(
        default=0.8,
        description="Threshold to start compression",
    )
    deduplicate: bool = Field(
        default=True,
        description="Whether to deduplicate content",
    )
    preserve_structure: bool = Field(
        default=True,
        description="Whether to preserve structure",
    )
    priority_ordering: bool = Field(
        default=True,
        description="Whether to order by priority",
    )
