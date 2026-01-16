"""
Execution Conflict Model for Execution Order Resolution.

This module defines ModelExecutionConflict, which represents a conflict
detected during execution order resolution. Conflicts include cycles in
dependency graphs, unsatisfiable constraints, and other ordering problems.

This is a pure data model with no side effects.

See Also:
    - OMN-1106: Beta Execution Order Resolution Pure Function
    - OMN-1227: ProtocolConstraintValidator for SPI
    - OMN-1292: Core Models for ProtocolConstraintValidator
    - ModelExecutionPlan: Contains the list of detected conflicts
    - ModelExecutionConstraints: The source of constraints that may conflict

.. versionadded:: 0.4.1
    Added as part of Execution Order Resolution (OMN-1106)
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelExecutionConflict(BaseModel):
    """
    Describes a conflict detected during execution order resolution.

    A conflict occurs when the declared constraints cannot be satisfied.
    Common conflict types include:
    - CYCLE: Circular dependency (A requires B, B requires A)
    - UNSATISFIABLE: Constraint references non-existent handler/capability
    - PHASE_CONFLICT: Handler constrained to run in incompatible phases
    - DUPLICATE_HANDLER: Same handler appears multiple times
    - MUST_RUN_CONFLICT: Conflicting must_run declarations between handlers

    The model is immutable (frozen) to ensure thread safety and prevent
    modification after resolution.

    Attributes:
        conflict_type: Category of the conflict (e.g., 'cycle', 'must_run_conflict')
        severity: How critical the conflict is ('error' blocks execution, 'warning' is advisory)
        message: Human-readable description of the conflict
        handler_ids: Immutable tuple of handler IDs involved in the conflict
        constraint_refs: Immutable tuple of constraint references involved (e.g., 'capability:auth')
        cycle_path: For CYCLE conflicts, immutable tuple representing the ordered path forming the cycle
        phase: Phase where conflict was detected (if applicable)
        suggested_resolution: Optional suggestion for resolving the conflict

    Example:
        >>> # Cycle conflict
        >>> conflict = ModelExecutionConflict(
        ...     conflict_type="cycle",
        ...     severity="error",
        ...     message="Circular dependency detected: A -> B -> A",
        ...     handler_ids=("handler.a", "handler.b"),
        ...     cycle_path=("handler.a", "handler.b", "handler.a"),
        ... )
        >>> conflict.is_blocking()
        True

        >>> # Unsatisfiable constraint (warning)
        >>> warning = ModelExecutionConflict(
        ...     conflict_type="unsatisfiable",
        ...     severity="warning",
        ...     message="Constraint 'capability:unknown' has no matching handlers",
        ...     constraint_refs=("capability:unknown",),
        ...     suggested_resolution="Remove the constraint or add a handler providing 'unknown'",
        ... )
        >>> warning.is_blocking()
        False

    Note:
        **Cycle Detection Behavior (Fail-Fast)**: The ExecutionResolver uses
        fail-fast cycle detection, meaning it returns immediately after detecting
        the first cycle. This is intentional for performance and simplicity:

        - Only the **first** cycle encountered is detected and reported
        - Additional cycles in the graph (if any) are NOT reported
        - This is sufficient because a single cycle invalidates the entire
          execution plan, making further detection unnecessary
        - For comprehensive detection of all strongly connected components,
          consider Tarjan's SCC algorithm (potential future enhancement)

        When a cycle is detected, the resolution stops immediately and returns
        an invalid plan. Users should fix the reported cycle and re-run
        resolution to discover any additional cycles.

    See Also:
        - ModelExecutionPlan: Contains conflicts detected during resolution
        - ExecutionResolver._detect_cycles: The cycle detection implementation

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

    conflict_type: Literal[
        "cycle",
        "unsatisfiable",
        "phase_conflict",
        "duplicate_handler",
        "missing_dependency",
        "constraint_violation",
        "must_run_conflict",
    ] = Field(
        ...,
        description="Category of the conflict",
    )

    severity: Literal["error", "warning"] = Field(
        ...,
        description="Severity level: 'error' blocks execution, 'warning' is advisory",
    )

    message: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of the conflict",
    )

    handler_ids: tuple[str, ...] = Field(
        default=(),
        description=(
            "Immutable tuple of handler IDs involved in the conflict. "
            "Empty tuple if no specific handlers are involved. "
            "For CYCLE conflicts, these are the handlers forming the cycle. "
            "For MUST_RUN_CONFLICT, these are the handlers with conflicting declarations."
        ),
    )

    constraint_refs: tuple[str, ...] = Field(
        default=(),
        description=(
            "Immutable tuple of constraint references involved in the conflict. "
            "Format is typically 'type:value' (e.g., 'capability:auth', 'must_run:handler.a'). "
            "Empty tuple if no specific constraints are involved."
        ),
    )

    cycle_path: tuple[str, ...] | None = Field(
        default=None,
        description=(
            "For CYCLE conflicts, the immutable ordered path forming the cycle. "
            "The first and last elements are the same handler, showing the cycle closure. "
            "For example: ('handler.a', 'handler.b', 'handler.a') represents A -> B -> A. "
            "None for non-cycle conflicts."
        ),
    )

    phase: str | None = Field(
        default=None,
        description="Execution phase where the conflict was detected",
    )

    suggested_resolution: str | None = Field(
        default=None,
        description="Suggested action to resolve the conflict",
    )

    @model_validator(mode="after")
    def validate_cycle_path_for_cycle_type(self) -> "ModelExecutionConflict":
        """
        Validate that cycle_path is provided for cycle conflicts.

        Returns:
            The validated conflict.

        Raises:
            ValueError: If conflict_type is 'cycle' but cycle_path is missing.
        """
        if self.conflict_type == "cycle" and not self.cycle_path:
            raise ValueError(
                "cycle_path must be provided when conflict_type is 'cycle'"
            )
        return self

    def is_blocking(self) -> bool:
        """
        Check if this conflict blocks execution.

        Returns:
            True if severity is 'error', False for 'warning'.
        """
        return self.severity == "error"

    def is_cycle(self) -> bool:
        """
        Check if this is a cycle conflict.

        Returns:
            True if conflict_type is 'cycle'.
        """
        return self.conflict_type == "cycle"

    def involves_handler(self, handler_id: str) -> bool:
        """
        Check if a specific handler is involved in this conflict.

        Args:
            handler_id: The handler ID to check.

        Returns:
            True if the handler is in handler_ids or cycle_path.
        """
        if handler_id in self.handler_ids:
            return True
        if self.cycle_path and handler_id in self.cycle_path:
            return True
        return False

    def get_cycle_length(self) -> int | None:
        """
        Get the length of the cycle (for cycle conflicts).

        Returns:
            Number of unique handlers in the cycle, or None if not a cycle.
        """
        if not self.cycle_path:
            return None
        # Cycle path includes the starting node at the end, so subtract 1
        return len(self.cycle_path) - 1

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"Conflict({self.conflict_type}/{self.severity}): {self.message}"

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelExecutionConflict(conflict_type={self.conflict_type!r}, "
            f"severity={self.severity!r}, "
            f"message={self.message!r}, "
            f"handler_ids={self.handler_ids!r})"
        )


__all__ = [
    "ModelExecutionConflict",
]
