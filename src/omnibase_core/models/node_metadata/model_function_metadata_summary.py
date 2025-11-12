"""Function Metadata Summary Model.

Type-safe dictionary for function metadata summary.
"""

from typing import TYPE_CHECKING, Any

from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue
from omnibase_core.types.typed_dict_deprecation_summary import (
    TypedDictDeprecationSummary,
)
from omnibase_core.types.typed_dict_documentation_summary_filtered import (
    TypedDictDocumentationSummaryFiltered,
)


class ModelFunctionMetadataSummary(dict[str, Any]):
    """Type-safe dictionary for function metadata summary."""

    documentation: TypedDictDocumentationSummaryFiltered  # Properly typed documentation summary (quality_score handled separately)
    deprecation: TypedDictDeprecationSummary  # Properly typed deprecation summary
    relationships: dict[
        str,
        ModelMetadataValue,
    ]  # *_count (int), has_* (bool), primary_category (str, "None" for missing)
    documentation_quality_score: float
    is_fully_documented: bool
    deprecation_status: str
