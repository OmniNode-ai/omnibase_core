"""
TypedDict for collection metadata.

Strongly-typed representation for metadata tool collection metadata.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict


class TypedDictCollectionMetadata(TypedDict):
    """Metadata about the tool collection."""

    id: str  # Serialization boundary - string ID appropriate for collection metadata
    tool_count: int
    health_score: float
    generated_at: str


__all__ = ["TypedDictCollectionMetadata"]
