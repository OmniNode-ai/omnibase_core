"""
Strongly-typed operation payload structure.

Replaces dict[str, Any] usage in operation payloads with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.operations.model_execution_metadata import (
    ModelExecutionMetadata,
)


class ModelOperationPayload(BaseModel):
    """
    Strongly-typed operation payload.

    Replaces dict[str, Any] with structured operation payload model.
    """

    operation_id: UUID = Field(
        default_factory=uuid4, description="Unique operation identifier (UUID format)"
    )
    operation_type: str = Field(..., description="Type of operation")
    input_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Operation input data with proper typing"
    )
    output_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Operation output data with proper typing"
    )
    parameters: dict[str, str] = Field(
        default_factory=dict, description="Operation parameters"
    )
    execution_metadata: ModelExecutionMetadata | None = Field(
        None, description="Execution metadata for the operation"
    )


# Export for use
__all__ = ["ModelOperationPayload"]
