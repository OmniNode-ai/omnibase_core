"""
Base operation data with discriminator.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

from .model_operation_payload_parameters_base import ModelOperationParametersBase


class ModelOperationDataBase(BaseModel):
    """Base operation data with discriminator."""

    operation_type: EnumNodeType = Field(
        default=...,
        description="Operation type discriminator",
    )
    input_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Operation input data with proper typing",
    )
    output_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Operation output data with proper typing",
    )
    parameters: ModelOperationParametersBase = Field(
        default_factory=ModelOperationParametersBase,
        description="Structured operation parameters",
    )


__all__ = ["ModelOperationDataBase"]
