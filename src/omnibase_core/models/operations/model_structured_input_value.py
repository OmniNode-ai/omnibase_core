"""
Strongly-typed structured input value model.

Represents structured data inputs for computation operations.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_input_data_type import EnumInputDataType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelStructuredInputValue(BaseModel):
    """
    Strongly-typed structured input value for computation operations.

    Represents structured data inputs with explicit field definitions.
    """

    input_type: EnumInputDataType = Field(
        default=EnumInputDataType.STRUCTURED,
        description="Type identifier for structured input data",
    )
    data_structure: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Structured data with field definitions",
    )
    schema_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Schema version for the structured data",
    )
    metadata: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Additional metadata for structured input",
    )

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )


# Export for use
__all__ = ["ModelStructuredInputValue"]
