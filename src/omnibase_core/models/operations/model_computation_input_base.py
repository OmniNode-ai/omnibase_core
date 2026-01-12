from __future__ import annotations

from pydantic import Field

"\nBase computation input model for discriminated union.\n\nProvides common interface for all computation input types.\nFollows ONEX strong typing principles and one-model-per-file architecture.\n"
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_computation_type import EnumComputationType
from omnibase_core.enums.enum_input_data_type import EnumInputDataType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelComputationInputBase(BaseModel):
    """
    Base model for computation inputs with discriminated union support.

    Provides common interface and type safety for all computation operations.
    """

    computation_type: EnumComputationType = Field(
        description="Type of computation operation"
    )
    input_data_type: EnumInputDataType = Field(
        description="Type of input data structure"
    )
    input_id: UUID = Field(description="Unique identifier for this input")
    timestamp: str = Field(description="Timestamp of input creation")
    priority: int = Field(
        default=0, description="Priority level for execution ordering"
    )
    metadata: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Additional metadata for computation input"
    )
    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )


__all__ = ["ModelComputationInputBase"]
