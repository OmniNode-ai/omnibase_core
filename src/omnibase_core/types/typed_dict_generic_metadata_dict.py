"""
TypedDict for generic metadata dictionary.

Strongly-typed representation for generic metadata dictionary structure.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict
from uuid import UUID

if TYPE_CHECKING:
    from omnibase_core.models.primitives.model_semver import ModelSemVer


class TypedDictGenericMetadataDict(TypedDict, total=False):
    """Strongly-typed structure for generic metadata dictionary in protocol methods."""

    metadata_id: UUID | None
    metadata_display_name: str | None
    description: str | None
    version: ModelSemVer | None
    tags: list[str]
    custom_fields: dict[str, object]


__all__ = ["TypedDictGenericMetadataDict"]
