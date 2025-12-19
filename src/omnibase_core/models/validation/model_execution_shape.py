"""
Execution Shape Model.

Model for representing a canonical ONEX execution shape.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_execution_shape import (
    EnumExecutionShape,
    EnumMessageCategory,
)
from omnibase_core.enums.enum_node_kind import EnumNodeKind

__all__ = [
    "ModelExecutionShape",
]


class ModelExecutionShape(BaseModel):
    """
    Represents a single execution shape definition.

    An execution shape defines a valid pattern for message flow from a
    source message category to a target node type in the ONEX architecture.

    Example:
        >>> shape = ModelExecutionShape(
        ...     shape=EnumExecutionShape.EVENT_TO_ORCHESTRATOR,
        ...     source_category=EnumMessageCategory.EVENT,
        ...     target_node_kind=EnumNodeKind.ORCHESTRATOR,
        ...     description="Events routed to orchestrators for workflow coordination",
        ... )
        >>> shape.shape
        <EnumExecutionShape.EVENT_TO_ORCHESTRATOR: 'event_to_orchestrator'>
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    shape: EnumExecutionShape = Field(
        ...,
        description="The canonical execution shape identifier",
    )
    source_category: EnumMessageCategory = Field(
        ...,
        description="The message category that initiates this shape",
    )
    target_node_kind: EnumNodeKind = Field(
        ...,
        description="The node kind that receives this shape",
    )
    description: str = Field(
        default="",
        description="Human-readable description of this execution shape",
    )

    @classmethod
    def from_shape(cls, shape: EnumExecutionShape) -> ModelExecutionShape:
        """
        Create a ModelExecutionShape from an EnumExecutionShape.

        Args:
            shape: The execution shape enum value

        Returns:
            A fully populated ModelExecutionShape
        """
        target_kind_str = EnumExecutionShape.get_target_node_kind(shape)
        target_kind = EnumNodeKind(target_kind_str)
        return cls(
            shape=shape,
            source_category=EnumExecutionShape.get_source_category(shape),
            target_node_kind=target_kind,
            description=EnumExecutionShape.get_description(shape),
        )

    @classmethod
    def get_all_shapes(cls) -> list[ModelExecutionShape]:
        """
        Get all canonical execution shapes as model instances.

        Returns:
            List of all ModelExecutionShape instances
        """
        return [cls.from_shape(shape) for shape in EnumExecutionShape]
