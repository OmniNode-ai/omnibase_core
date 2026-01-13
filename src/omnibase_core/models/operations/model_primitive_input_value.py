"""
Strongly-typed primitive input value model.

Represents primitive data inputs for computation operations.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_input_data_type import EnumInputDataType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelPrimitiveInputValue(BaseModel):
    """
    Strongly-typed primitive input value for computation operations.

    Represents primitive data inputs like strings, numbers, booleans.
    """

    input_type: EnumInputDataType = Field(
        default=EnumInputDataType.PRIMITIVE,
        description="Type identifier for primitive input data",
    )
    value: ModelSchemaValue = Field(
        description="Primitive value (string, number, boolean, etc.)",
    )
    value_type: str = Field(
        description="Explicit type of the primitive value",
    )
    unit: str | None = Field(
        default=None,
        description="Optional unit for numeric values",
    )
    metadata: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Additional metadata for primitive input",
    )

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )


# Export for use
__all__ = ["ModelPrimitiveInputValue"]
