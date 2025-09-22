"""
Generic collection summary model.

Strongly-typed summary for generic collections that replaces Dict[str, Any]
anti-pattern with proper type safety.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelGenericCollectionSummary(BaseModel):
    """
    Strongly-typed summary for generic collections.

    Replaces Dict[str, Any] anti-pattern with proper type safety.
    """

    collection_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the collection",
    )
    collection_display_name: str = Field(
        default="",
        description="Human-readable display name for the collection",
    )
    total_items: int = Field(description="Total number of items in collection")
    enabled_items: int = Field(description="Number of enabled items")
    valid_items: int = Field(description="Number of valid items")
    created_at: datetime = Field(description="When the collection was created")
    updated_at: datetime = Field(description="When the collection was last modified")
    has_items: bool = Field(description="Whether the collection contains any items")


# Export for use
__all__ = ["ModelGenericCollectionSummary"]
