"""Function Metadata Summary Model.

Type-safe dictionary for function metadata summary.
"""

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


class ModelFunctionMetadataSummary(TypedDict):
    """Type-safe dictionary for function metadata summary."""

    documentation: TypedDictDocumentationSummaryFiltered
    deprecation: TypedDictDeprecationSummary
    relationships: TypedDictFunctionRelationshipsSummary
    documentation_quality_score: float
    is_fully_documented: bool
    deprecation_status: str


__all__ = ["ModelFunctionMetadataSummary"]
