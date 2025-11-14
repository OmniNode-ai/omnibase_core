from __future__ import annotations

from pydantic import Field

"""
Strongly-typed mixed input value model.

Represents mixed data inputs combining structured and primitive data.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from typing import Any

from pydantic import BaseModel

from omnibase_core.enums.enum_input_data_type import EnumInputDataType


class ModelMixedInputValue(BaseModel):
    """
    Strongly-typed mixed input value for computation operations.

    Represents mixed data inputs combining structured and primitive elements.
    """

    input_type: EnumInputDataType = Field(
        default=EnumInputDataType.MIXED,
        description="Type identifier for mixed input data",
    )
    primary_value: Any = Field(
        description="Primary primitive or structured value",
    )
    secondary_values: list[Any] = Field(
        default_factory=list,
        description="List of secondary values of mixed types",
    )
    value_hierarchy: list[str] = Field(
        default_factory=list,
        description="Hierarchy defining value precedence",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for mixed input",
    )

    model_config = {
        "extra": "forbid",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for use
__all__ = ["ModelMixedInputValue"]
