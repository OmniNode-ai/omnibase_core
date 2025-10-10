"""TypedDict for usage metadata structure."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class TypedDictUsageMetadata(TypedDict, total=False):
    """Typed structure for usage metadata dictionary in protocol methods.

    Used by metadata provider protocols to ensure consistent metadata structure
    across node implementations.
    """

    name: NotRequired[str]
    description: NotRequired[str]
    version: NotRequired[str]  # String representation of ModelSemVer
    tags: NotRequired[list[str]]
    metadata: NotRequired[dict[str, str]]
