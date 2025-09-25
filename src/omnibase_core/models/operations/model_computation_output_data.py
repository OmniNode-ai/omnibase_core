"""
Strongly-typed computation output data model.

Replaces dict[str, Any] usage in computation output operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelComputationOutputData(BaseModel):
    """
    Strongly-typed output data for computation operations.

    Replaces dict[str, Any] with structured result model.
    """

    computed_values: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Computed result values with proper typing"
    )
    metrics: dict[str, float] = Field(
        default_factory=dict, description="Numeric metrics from computation"
    )
    status_flags: dict[str, bool] = Field(
        default_factory=dict, description="Boolean status indicators"
    )
    output_metadata: dict[str, str] = Field(
        default_factory=dict, description="String metadata about the results"
    )
    processing_info: dict[str, str] = Field(
        default_factory=dict, description="Processing information and diagnostics"
    )


# Export for use
__all__ = ["ModelComputationOutputData"]
