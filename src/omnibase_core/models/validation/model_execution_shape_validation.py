"""
Execution Shape Validation Model.

Model for validating execution shapes against canonical ONEX patterns.
"""

from __future__ import annotations

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
    to the canonical ONEX execution shapes.

    Example:
        >>> validation = ModelExecutionShapeValidation(
        ...     source_category=EnumMessageCategory.EVENT,
        ...     target_node_kind=EnumNodeKind.ORCHESTRATOR,
        ...     is_allowed=True,
        ...     matched_shape=EnumExecutionShape.EVENT_TO_ORCHESTRATOR,
        ...     rationale="Matches canonical EVENT_TO_ORCHESTRATOR shape",
        ... )
        >>> validation.is_allowed
        True
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

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
    ) -> ModelExecutionShapeValidation:
        """
        Validate if a proposed execution shape is allowed.

        Args:
            source_category: The message category that initiates the flow
            target_node_kind: The node kind that would receive the message

        Returns:
            A ModelExecutionShapeValidation indicating if the shape is valid
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
