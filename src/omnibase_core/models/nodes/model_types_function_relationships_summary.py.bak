from __future__ import annotations

from typing import Dict, TypedDict

"""
TypedDict for function relationships summary.

Replaces dict[str, Any] return type with structured typing.
"""


from typing import TypedDict


class ModelFunctionRelationshipsSummaryType(TypedDict):
    """
    Typed dict[str, Any]ionary for function relationships summary.

    Replaces dict[str, Any] return type from get_relationships_summary()
    with proper type structure.
    """

    dependencies_count: int
    related_functions_count: int
    tags_count: int
    categories_count: int
    has_dependencies: bool
    has_related_functions: bool
    has_tags: bool
    has_categories: bool
    primary_category: str


# Export for use
__all__ = ["ModelFunctionRelationshipsSummaryType"]
