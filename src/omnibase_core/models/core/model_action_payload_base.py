"""
Action Payload Base Model.

Base class for action-specific payload types with common fields and validation.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelActionPayloadBase(BaseModel):
    """
    Base class for action-specific payload types.

    Provides common fields and validation for all action payload types.
    """

    action_type: ModelNodeActionType = Field(
        default=...,
        description="The rich action type being performed",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracking this action",
    )
    metadata: SerializedDict = Field(
        default_factory=dict,
        description="Additional metadata for the action",
    )

    model_config = ConfigDict(use_enum_values=True)
