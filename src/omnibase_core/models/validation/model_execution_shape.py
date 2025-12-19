"""
Execution Shape Model.

Model for representing a canonical ONEX execution shape. This model provides
a structured representation of valid message flow patterns in the ONEX
four-node architecture.

See Also:
    - EnumExecutionShape: The underlying enum defining canonical shapes
    - CANONICAL_EXECUTION_SHAPES.md: Full documentation of execution patterns
"""

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
    This model wraps the EnumExecutionShape with additional metadata for
    validation and introspection.

    Attributes:
        shape: The canonical execution shape identifier (e.g., EVENT_TO_ORCHESTRATOR)
        source_category: The message category that initiates this shape (EVENT, COMMAND, INTENT)
        target_node_kind: The node kind that receives this shape (ORCHESTRATOR, REDUCER, EFFECT)
        description: Human-readable description explaining the shape's purpose

    Example:
        >>> # Create from enum using factory method (recommended)
        >>> shape = ModelExecutionShape.from_shape(EnumExecutionShape.EVENT_TO_ORCHESTRATOR)
        >>> shape.shape
        <EnumExecutionShape.EVENT_TO_ORCHESTRATOR: 'event_to_orchestrator'>
        >>> shape.source_category
        <EnumMessageCategory.EVENT: 'event'>
        >>> shape.target_node_kind
        <EnumNodeKind.ORCHESTRATOR: 'orchestrator'>

        >>> # Create directly with all fields
        >>> shape = ModelExecutionShape(
        ...     shape=EnumExecutionShape.EVENT_TO_ORCHESTRATOR,
        ...     source_category=EnumMessageCategory.EVENT,
        ...     target_node_kind=EnumNodeKind.ORCHESTRATOR,
        ...     description="Events routed to orchestrators for workflow coordination",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

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
    def from_shape(cls, shape: EnumExecutionShape) -> "ModelExecutionShape":
        """
        Create a ModelExecutionShape from an EnumExecutionShape.

        This factory method automatically populates all fields by extracting
        metadata from the enum value. This is the recommended way to create
        ModelExecutionShape instances.

        Args:
            shape: The execution shape enum value

        Returns:
            A fully populated ModelExecutionShape with source category,
            target node kind, and description automatically filled in

        Example:
            >>> shape = ModelExecutionShape.from_shape(EnumExecutionShape.INTENT_TO_EFFECT)
            >>> shape.source_category
            <EnumMessageCategory.INTENT: 'intent'>
            >>> shape.target_node_kind
            <EnumNodeKind.EFFECT: 'effect'>
            >>> shape.description
            'Intents routed to effects for external actions'
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
    def get_all_shapes(cls) -> "list[ModelExecutionShape]":
        """
        Get all canonical execution shapes as model instances.

        Returns all five canonical execution shapes defined in the ONEX
        architecture. Useful for validation, introspection, and documentation.

        Returns:
            List of all ModelExecutionShape instances, one for each
            canonical shape in EnumExecutionShape

        Example:
            >>> shapes = ModelExecutionShape.get_all_shapes()
            >>> len(shapes)
            5
            >>> [s.shape.value for s in shapes]  # doctest: +NORMALIZE_WHITESPACE
            ['event_to_orchestrator', 'event_to_reducer', 'intent_to_effect',
             'command_to_orchestrator', 'command_to_effect']
        """
        return [cls.from_shape(shape) for shape in EnumExecutionShape]
