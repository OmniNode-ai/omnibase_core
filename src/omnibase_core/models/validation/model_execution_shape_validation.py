"""
Execution Shape Validation Model.

Model for validating execution shapes against canonical ONEX patterns.
This model is used to check whether a proposed message flow pattern
conforms to the architectural constraints defined by the ONEX four-node
architecture.

See Also:
    - EnumExecutionShape: Defines the canonical shapes
    - ModelShapeValidationResult: Aggregates multiple validation results
    - CANONICAL_EXECUTION_SHAPES.md: Full documentation of allowed/forbidden patterns
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_execution_shape import (
    EnumExecutionShape,
    EnumMessageCategory,
)
from omnibase_core.enums.enum_node_kind import EnumNodeKind

__all__ = [
    "ModelExecutionShapeValidation",
]


class ModelExecutionShapeValidation(BaseModel):
    """
    Validates if a proposed execution shape is allowed.

    This model captures the result of validating whether a specific
    combination of message category and target node type conforms
    to the canonical ONEX execution shapes. Use the `validate_shape`
    factory method to perform validation.

    Attributes:
        source_category: The message category being validated (EVENT, COMMAND, INTENT)
        target_node_kind: The target node kind being validated (ORCHESTRATOR, REDUCER, EFFECT)
        is_allowed: Whether this shape conforms to ONEX canonical patterns
        matched_shape: The canonical shape that was matched, if allowed
        rationale: Explanation for why the shape is allowed or disallowed

    Example:
        >>> # Validate an allowed shape
        >>> validation = ModelExecutionShapeValidation.validate_shape(
        ...     source_category=EnumMessageCategory.EVENT,
        ...     target_node_kind=EnumNodeKind.ORCHESTRATOR,
        ... )
        >>> validation.is_allowed
        True
        >>> validation.matched_shape
        <EnumExecutionShape.EVENT_TO_ORCHESTRATOR: 'event_to_orchestrator'>

        >>> # Validate a forbidden shape
        >>> validation = ModelExecutionShapeValidation.validate_shape(
        ...     source_category=EnumMessageCategory.COMMAND,
        ...     target_node_kind=EnumNodeKind.REDUCER,
        ... )
        >>> validation.is_allowed
        False
        >>> validation.matched_shape is None
        True
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_category: EnumMessageCategory = Field(
        ...,
        description="The source message category being validated",
    )
    target_node_kind: EnumNodeKind = Field(
        ...,
        description="The target node kind being validated",
    )
    is_allowed: bool = Field(
        default=False,
        description="Whether this shape is allowed per ONEX canonical patterns",
    )
    matched_shape: EnumExecutionShape | None = Field(
        default=None,
        description="The canonical shape matched, if any",
    )
    rationale: str = Field(
        default="",
        description="Explanation for why the shape is allowed or disallowed",
    )

    @classmethod
    def validate_shape(
        cls,
        source_category: EnumMessageCategory,
        target_node_kind: EnumNodeKind,
    ) -> "ModelExecutionShapeValidation":
        """
        Validate if a proposed execution shape is allowed.

        Checks whether routing a message of the given category to the specified
        node kind conforms to ONEX canonical execution shapes. This is the
        primary validation method for enforcing architectural constraints.

        Args:
            source_category: The message category that initiates the flow
                (EVENT, COMMAND, or INTENT)
            target_node_kind: The node kind that would receive the message
                (ORCHESTRATOR, REDUCER, EFFECT, or COMPUTE)

        Returns:
            A ModelExecutionShapeValidation with:
            - is_allowed=True and matched_shape set if the pattern is valid
            - is_allowed=False and rationale explaining why if the pattern is invalid

        Example:
            >>> # Valid: Events can route to orchestrators
            >>> result = ModelExecutionShapeValidation.validate_shape(
            ...     EnumMessageCategory.EVENT,
            ...     EnumNodeKind.ORCHESTRATOR,
            ... )
            >>> result.is_allowed
            True

            >>> # Invalid: Commands cannot route directly to reducers
            >>> result = ModelExecutionShapeValidation.validate_shape(
            ...     EnumMessageCategory.COMMAND,
            ...     EnumNodeKind.REDUCER,
            ... )
            >>> result.is_allowed
            False
            >>> 'No canonical shape' in result.rationale
            True
        """
        # Find matching canonical shape
        for shape in EnumExecutionShape:
            shape_source = EnumExecutionShape.get_source_category(shape)
            shape_target_str = EnumExecutionShape.get_target_node_kind(shape)

            if (
                shape_source == source_category
                and shape_target_str == target_node_kind.value
            ):
                return cls(
                    source_category=source_category,
                    target_node_kind=target_node_kind,
                    is_allowed=True,
                    matched_shape=shape,
                    rationale=f"Matches canonical {shape.value} shape: {EnumExecutionShape.get_description(shape)}",
                )

        # No matching shape found
        return cls(
            source_category=source_category,
            target_node_kind=target_node_kind,
            is_allowed=False,
            matched_shape=None,
            rationale=f"No canonical shape allows {source_category.value} messages to {target_node_kind.value} nodes",
        )
