"""TypedDict for usage metadata structure."""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from omnibase_core.models.primitives.model_semver import ModelSemVer


class TypedDictUsageMetadata(TypedDict, total=False):
    """Typed structure for usage metadata dictionary in protocol methods.

    Used by metadata provider protocols to ensure consistent metadata structure
    across node implementations.
    """

    name: NotRequired[str]
    description: NotRequired[str]
    version: NotRequired[ModelSemVer]
    tags: NotRequired[list[str]]
    metadata: NotRequired[dict[str, str]]


__all__ = ["TypedDictUsageMetadata"]
