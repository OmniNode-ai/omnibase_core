"""TypedDictCollectionCreateKwargs.

Type-safe dict[str, Any]ionary for collection creation parameters.
"""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID


class TypedDictCollectionCreateKwargs(TypedDict, total=False):
    """Type-safe dict[str, Any]ionary for collection creation parameters."""

    collection_display_name: str
    collection_id: UUID
