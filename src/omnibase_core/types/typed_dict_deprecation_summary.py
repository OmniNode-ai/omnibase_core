"""
TypedDict for deprecation summary.

Strongly-typed representation for deprecation summary information.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictDeprecationSummary(TypedDict):
    """Strongly-typed dictionary for deprecation summary."""

    is_deprecated: bool
    has_replacement: bool
    deprecated_since: str | None
    replacement: str | None
    status: str  # EnumDeprecationStatus.value


__all__ = ["TypedDictDeprecationSummary"]
