"""
TypedDict for function metadata summary.

Strongly-typed representation for function metadata summary information.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict

from omnibase_core.types.typed_dict_deprecation_summary import (
    TypedDictDeprecationSummary,
)
from omnibase_core.types.typed_dict_documentation_summary_filtered import (
    TypedDictDocumentationSummaryFiltered,
)
from omnibase_core.types.typed_dict_function_relationships_summary import (
    TypedDictFunctionRelationshipsSummary,
)


class TypedDictFunctionMetadataSummary(TypedDict):
    """Strongly-typed dictionary for function metadata summary."""

    documentation: TypedDictDocumentationSummaryFiltered
    deprecation: TypedDictDeprecationSummary
    relationships: TypedDictFunctionRelationshipsSummary
    documentation_quality_score: float
    is_fully_documented: bool
    deprecation_status: str


__all__ = ["TypedDictFunctionMetadataSummary"]
