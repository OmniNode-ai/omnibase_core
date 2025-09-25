"""
Collection TypedDict definitions.

Type-safe dictionary definitions for collection creation parameters.
"""

from __future__ import annotations

from typing import Any, TypedDict
from uuid import UUID


class TypedDictCollectionCreateKwargs(TypedDict, total=False):
    """Type-safe dictionary for collection creation parameters."""

    collection_display_name: str
    collection_id: UUID


class TypedDictCollectionFromItemsKwargs(TypedDict, total=False):
    """Type-safe dictionary for collection creation from items parameters."""

    items: list[Any]  # Don't import BaseModel from types - use Any
    collection_display_name: str
    collection_id: UUID
