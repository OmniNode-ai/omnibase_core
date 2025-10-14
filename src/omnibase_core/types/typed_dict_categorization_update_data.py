"""
TypedDict for categorization update data.

Strongly-typed representation for categorization data updates.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict


class TypedDictCategorizationUpdateData(TypedDict, total=False):
    """Strongly-typed structure for categorization data updates."""

    technical_tags: list[str]
    business_tags: list[str]
    domain_tags: list[str]
    complexity_tags: list[str]


__all__ = ["TypedDictCategorizationUpdateData"]
