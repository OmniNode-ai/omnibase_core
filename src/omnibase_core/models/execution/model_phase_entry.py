"""
Phase Entry Model for Execution Order Resolution.

This module defines ModelPhaseEntry, representing a single handler's entry
in an execution phase. Each entry captures the handler's resolved position,
the constraints that were evaluated, and metadata about the resolution decision.

This is a pure data model with no side effects.

See Also:
    - OMN-1106: Beta Execution Order Resolution Pure Function
    - ModelExecutionPlan: The plan that contains phase entries
    - ModelExecutionConstraints: The constraints that are evaluated

.. versionadded:: 0.4.1
    Added as part of Execution Order Resolution (OMN-1106)
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.execution.model_constraint_satisfaction import (
    ModelConstraintSatisfaction,
)


class ModelPhaseEntry(BaseModel):
    """
    A single handler's entry in an execution phase.

    This model represents one handler's position in the resolved execution order
    for a specific phase. It includes the handler's resolved position, the
    constraints that were evaluated, and metadata about how the position was
    determined.

    The model is immutable (frozen) to ensure thread safety and prevent
    accidental modification after resolution.

    Attributes:
        handler_ref: Handler reference identifier (e.g., "handler.user.validator")
        position: Zero-based position within the phase (0 = first to execute)
        constraints_evaluated: List of constraints that were checked for this handler
        all_constraints_satisfied: True if all declared constraints were met
        parallel_eligible: Whether this handler can run in parallel with others
        tie_breaker_applied: Name of tie-breaker used if ordering was ambiguous
        resolution_notes: Optional notes about how position was determined

    Example:
        >>> from omnibase_core.models.execution.model_phase_entry import (
        ...     ModelPhaseEntry,
        ... )
        >>> from omnibase_core.models.execution.model_constraint_satisfaction import (
        ...     ModelConstraintSatisfaction,
        ... )
        >>> entry = ModelPhaseEntry(
        ...     handler_ref="handler.user.validator",
        ...     position=0,
        ...     constraints_evaluated=[
        ...         ModelConstraintSatisfaction(
        ...             constraint_ref="capability:auth",
        ...             constraint_type="requires_before",
        ...             satisfied=True,
        ...             resolved_to_handlers=["handler.auth.provider"],
        ...         ),
        ...     ],
        ...     all_constraints_satisfied=True,
        ...     parallel_eligible=False,
        ... )
        >>> entry.position
        0

    See Also:
        - ModelExecutionPlan: Contains phase entries organized by phase
        - ModelExecutionConstraints: Defines the constraints being evaluated

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    .. versionadded:: 0.4.1
        Added as part of Execution Order Resolution (OMN-1106)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    handler_ref: str = Field(
        ...,
        min_length=1,
        description="Handler reference identifier (e.g., 'handler.user.validator')",
    )

    position: int = Field(
        ...,
        ge=0,
        description="Zero-based position within the phase (0 = first to execute)",
    )

    constraints_evaluated: list[ModelConstraintSatisfaction] = Field(
        default_factory=list,
        description="List of constraints that were checked for this handler",
    )

    all_constraints_satisfied: bool = Field(
        default=True,
        description="True if all declared constraints were met in the ordering",
    )

    parallel_eligible: bool = Field(
        default=True,
        description="Whether this handler can run in parallel with adjacent handlers",
    )

    tie_breaker_applied: str | None = Field(
        default=None,
        description="Name of tie-breaker used if ordering was ambiguous (e.g., 'priority', 'alphabetical')",
    )

    resolution_notes: str | None = Field(
        default=None,
        description="Optional notes about how position was determined",
    )

    def has_unsatisfied_constraints(self) -> bool:
        """
        Check if any constraints were not satisfied.

        Returns:
            True if any constraint in constraints_evaluated has satisfied=False.
        """
        return any(not c.satisfied for c in self.constraints_evaluated)

    def get_unsatisfied_constraints(self) -> list[ModelConstraintSatisfaction]:
        """
        Get list of unsatisfied constraints.

        Returns:
            List of ModelConstraintSatisfaction where satisfied=False.
        """
        return [c for c in self.constraints_evaluated if not c.satisfied]

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        status = "OK" if self.all_constraints_satisfied else "UNSATISFIED"
        return f"PhaseEntry({self.handler_ref}@{self.position}, {status})"

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelPhaseEntry(handler_ref={self.handler_ref!r}, "
            f"position={self.position}, "
            f"all_constraints_satisfied={self.all_constraints_satisfied}, "
            f"parallel_eligible={self.parallel_eligible}, "
            f"tie_breaker_applied={self.tie_breaker_applied!r})"
        )


__all__ = [
    "ModelPhaseEntry",
]
