"""
Constraint Satisfaction Model for Execution Order Resolution.

This module defines ModelConstraintSatisfaction, which records whether
a specific constraint was satisfied during resolution.

This is a pure data model with no side effects.

See Also:
    - OMN-1106: Beta Execution Order Resolution Pure Function
    - ModelPhaseEntry: Contains constraint satisfaction records
    - ModelExecutionConstraints: The constraints that are evaluated

.. versionadded:: 0.4.1
    Added as part of Execution Order Resolution (OMN-1106)
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelConstraintSatisfaction(BaseModel):
    """
    Records whether a specific constraint was satisfied during resolution.

    This model tracks individual constraint evaluations, allowing inspection
    of the resolution process for debugging and auditing.

    Attributes:
        constraint_ref: The constraint reference (e.g., "capability:auth", "handler:metrics")
        constraint_type: Type of constraint ("requires_before" or "requires_after")
        satisfied: Whether the constraint was satisfied in the final ordering
        resolved_to_handlers: Handler IDs that matched this constraint reference
        notes: Optional notes about the constraint resolution

    Example:
        >>> satisfaction = ModelConstraintSatisfaction(
        ...     constraint_ref="capability:auth",
        ...     constraint_type="requires_before",
        ...     satisfied=True,
        ...     resolved_to_handlers=["handler.auth.validator"],
        ... )

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    .. versionadded:: 0.4.1
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    constraint_ref: str = Field(
        ...,
        min_length=1,
        description="The constraint reference (e.g., 'capability:auth', 'handler:metrics')",
    )

    constraint_type: str = Field(
        ...,
        description="Type of constraint: 'requires_before' or 'requires_after'",
    )

    satisfied: bool = Field(
        ...,
        description="Whether this constraint was satisfied in the final ordering",
    )

    resolved_to_handlers: list[str] = Field(
        default_factory=list,
        description="Handler IDs that matched this constraint reference",
    )

    notes: str | None = Field(
        default=None,
        description="Optional notes about constraint resolution",
    )


__all__ = [
    "ModelConstraintSatisfaction",
]
