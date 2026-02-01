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
    Implements ProtocolActionPayload via the `kind` property.
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

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)

    @property
    def kind(self) -> str:
        """Action type identifier for routing (implements ProtocolActionPayload).

        Returns the action type name for dispatch/routing purposes.
        This property enables all subclasses to automatically satisfy
        the ProtocolActionPayload protocol.

        Returns:
            str: The action type name (e.g., "start", "complete", "transform").
        """
        return self.action_type.name
