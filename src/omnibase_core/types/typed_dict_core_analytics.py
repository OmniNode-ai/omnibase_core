"""
TypedDict for core analytics data.

Strongly-typed representation for core analytics data structure.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict
from uuid import UUID


class TypedDictCoreAnalytics(TypedDict):
    """Strongly-typed core analytics data structure."""

    collection_id: UUID
    collection_name: str | None
    total_nodes: int
    active_nodes: int
    deprecated_nodes: int
    disabled_nodes: int
    has_issues: bool


__all__ = ["TypedDictCoreAnalytics"]
