"""
Strongly-typed operation parameters model.

Replaces dict[str, Any] usage in operation parameters with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelOperationParameters(BaseModel):
    """
    Strongly-typed operation parameters.

    Replaces dict[str, Any] with structured parameter model.
    """

    string_parameters: dict[str, str] = Field(
        default_factory=dict, description="String-based parameters"
    )
    numeric_parameters: dict[str, float] = Field(
        default_factory=dict, description="Numeric parameters"
    )
    boolean_parameters: dict[str, bool] = Field(
        default_factory=dict, description="Boolean parameters"
    )
    list_parameters: dict[str, list[str]] = Field(
        default_factory=dict, description="List-based parameters"
    )
    nested_parameters: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Complex nested parameters with proper typing"
    )


# Export for use
__all__ = ["ModelOperationParameters"]
