"""
Metadata for a node collection.

Provides comprehensive metadata about a collection of nodes including
counts, health scores, and generation timestamps.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelCollectionMetadata(BaseModel):
    """Metadata for a node collection."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        ...,
        description="Collection unique identifier",
    )
    node_count: int = Field(
        ...,
        description="Number of nodes in collection",
        ge=0,
    )
    health_score: float = Field(
        ...,
        description="Collection health score (0-100)",
        ge=0.0,
        le=100.0,
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Report generation timestamp",
    )
