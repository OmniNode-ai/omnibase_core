"""TypedDict for function relationships summary.

Type-safe dictionary for function relationships data.
"""

from typing import TypedDict


class TypedDictFunctionRelationshipsSummary(TypedDict):
    """Typed dictionary for function relationships summary.

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


__all__ = ["TypedDictFunctionRelationshipsSummary"]
