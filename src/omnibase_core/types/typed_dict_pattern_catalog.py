"""TypedDict for pattern catalog configuration."""

from __future__ import annotations

from typing import TypedDict


class TypedDictPatternCatalog(TypedDict, total=False):
    """Pattern catalog configuration for framework integration.

    Describes available patterns and coordination-specific patterns.
    """

    applicable_patterns: list[str]
    coordination_specific: list[str]


__all__ = ["TypedDictPatternCatalog"]
