"""TypedDictCollectionFromItemsKwargs.

Type-safe dictionary for collection creation from items parameters.
"""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID


class TypedDictCollectionFromItemsKwargs(TypedDict, total=False):
    """Type-safe dictionary for collection creation from items parameters."""

    items: list[object]  # ONEX compliance - use object instead of Any
    collection_display_name: str
    collection_id: UUID


__all__ = ["TypedDictCollectionFromItemsKwargs"]
