"""
TypedDict for tool breakdown.

Strongly-typed representation for breakdown of tools by various categories.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict


class TypedDictToolBreakdown(TypedDict):
    """Breakdown of tools by various categories."""

    by_type: dict[str, int]
    by_status: dict[str, int]
    by_complexity: dict[str, int]


__all__ = ["TypedDictToolBreakdown"]
