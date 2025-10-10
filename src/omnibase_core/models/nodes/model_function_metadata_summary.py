"""Function Metadata Summary Model.

Type-safe dictionary for function metadata summary.
"""

from typing import TYPE_CHECKING, Any, Dict

from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue
from omnibase_core.types.typed_dict_documentation_summary_filtered import (
    TypedDictDocumentationSummaryFiltered,
)

if TYPE_CHECKING:
    from .model_deprecation_summary import ModelDeprecationSummary


class ModelFunctionMetadataSummary(Dict[str, Any]):
    """Type-safe dictionary for function metadata summary."""

    documentation: TypedDictDocumentationSummaryFiltered  # Properly typed documentation summary (quality_score handled separately)
    deprecation: "ModelDeprecationSummary"  # Properly typed deprecation summary
    relationships: Dict[
        str,
        ModelMetadataValue,
    ]  # *_count (int), has_* (bool), primary_category (str, "None" for missing)
    documentation_quality_score: float
    is_fully_documented: bool
    deprecation_status: str
