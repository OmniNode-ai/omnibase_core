"""
Strongly-typed computation input data model.

Replaces dict[str, Any] usage in computation input operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelComputationInputData(BaseModel):
    """
    Strongly-typed input data for computation operations.

    Replaces dict[str, Any] with structured data model.
    """

    source_values: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Source values for computation with proper typing",
    )
    operation_parameters: dict[str, str] = Field(
        default_factory=dict, description="String-based operation parameters"
    )
    numeric_parameters: dict[str, float] = Field(
        default_factory=dict, description="Numeric parameters for calculations"
    )
    boolean_flags: dict[str, bool] = Field(
        default_factory=dict, description="Boolean configuration flags"
    )
    metadata_context: dict[str, str] = Field(
        default_factory=dict, description="String metadata context"
    )


# Export for use
__all__ = ["ModelComputationInputData"]
