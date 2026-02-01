"""
Execution Plan Model for Runtime Execution Sequencing.

This module defines the ModelExecutionPlan model which represents a resolved phase
ordering derived from a merged contract. It contains an ordered list of ModelPhaseStep
instances representing the complete execution sequence.

The model also supports the richer resolution metadata from OMN-1106, including
conflict detection, constraint satisfaction tracking, and tie-breaker decisions.

This is a pure data model with no side effects.

See Also:
    - OMN-1108: Runtime Execution Sequencing Model (original)
    - OMN-1106: Beta Execution Order Resolution Pure Function (resolution metadata)

.. versionadded:: 0.4.0
    Added as part of Runtime Execution Sequencing Model (OMN-1108)

.. versionchanged:: 0.4.1
    Added resolution metadata, conflicts, and validity tracking (OMN-1106)
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.models.execution.model_execution_conflict import (
    ModelExecutionConflict,
)
from omnibase_core.models.execution.model_phase_step import ModelPhaseStep
from omnibase_core.models.execution.model_resolution_metadata import (
    ModelResolutionMetadata,
)


class ModelExecutionPlan(BaseModel):
    """
    A resolved execution plan derived from a merged contract.

    This model represents the complete execution plan containing an ordered list
    of phase steps. It is the result of merging and resolving execution profiles
    according to an ordering policy.

    The plan includes resolution metadata (OMN-1106) that captures tie-breaker
    decisions, constraint satisfaction, and any conflicts detected during
    resolution. This enables debugging and auditing of the ordering process.

    The model is immutable (frozen) to ensure thread safety and prevent
    accidental modification during execution.

    Attributes:
        phases: Ordered list of phase steps defining the execution sequence
        source_profile: Identifier of the execution profile this was derived from
        ordering_policy: Description of the ordering policy used to create this plan
        created_at: Timestamp when this plan was created
        metadata: Optional metadata about this execution plan
        resolution_metadata: Detailed metadata about the resolution process (OMN-1106)
        conflicts: List of conflicts detected during resolution (OMN-1106)
        is_valid: Whether the plan is valid (no blocking conflicts) (OMN-1106)

    Example:
        >>> from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
        >>> from omnibase_core.models.execution.model_phase_step import ModelPhaseStep
        >>> from omnibase_core.models.execution.model_resolution_metadata import (
        ...     ModelResolutionMetadata,
        ... )
        >>> plan = ModelExecutionPlan(
        ...     phases=[
        ...         ModelPhaseStep(
        ...             phase=EnumHandlerExecutionPhase.PREFLIGHT,
        ...             handler_ids=["validate_input"]
        ...         ),
        ...         ModelPhaseStep(
        ...             phase=EnumHandlerExecutionPhase.EXECUTE,
        ...             handler_ids=["process_data", "transform_output"]
        ...         ),
        ...     ],
        ...     source_profile="orchestrator_safe",
        ...     ordering_policy="topological_sort",
        ...     resolution_metadata=ModelResolutionMetadata(
        ...         strategy="topological_sort",
        ...         total_handlers_resolved=3,
        ...     ),
        ...     is_valid=True,
        ... )
        >>> plan.total_handlers()
        3
        >>> plan.is_empty()
        False
        >>> plan.is_valid
        True

    See Also:
        - :class:`~omnibase_core.models.execution.model_phase_step.ModelPhaseStep`:
          The phase step model that makes up this plan
        - :class:`~omnibase_core.models.execution.model_resolution_metadata.ModelResolutionMetadata`:
          Metadata about the resolution process
        - :class:`~omnibase_core.models.execution.model_execution_conflict.ModelExecutionConflict`:
          Conflicts detected during resolution
        - :class:`~omnibase_core.models.contracts.model_execution_profile.ModelExecutionProfile`:
          The profile model that this plan is derived from
        - :class:`~omnibase_core.enums.enum_handler_execution_phase.EnumHandlerExecutionPhase`:
          The enum defining available execution phases

    .. versionadded:: 0.4.0
        Added as part of Runtime Execution Sequencing Model (OMN-1108)

    .. versionchanged:: 0.4.1
        Added resolution_metadata, conflicts, and is_valid fields (OMN-1106)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
        validate_assignment=True,
    )

    phases: list[ModelPhaseStep] = Field(
        default_factory=list,
        description="Ordered list of phase steps defining the execution sequence",
    )

    source_profile: str | None = Field(
        default=None,
        description="Identifier of the execution profile this plan was derived from",
    )

    ordering_policy: str | None = Field(
        default=None,
        description="Description of the ordering policy used to create this plan",
    )

    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when this plan was created",
    )

    metadata: dict[str, str | int | float | bool | None] | None = Field(
        default=None,
        description="Optional metadata about this execution plan",
    )

    # =========================================================================
    # Resolution Fields (OMN-1106)
    # =========================================================================

    resolution_metadata: ModelResolutionMetadata | None = Field(
        default=None,
        description="Detailed metadata about the resolution process (tie-breakers, timing, etc.)",
    )

    conflicts: list[ModelExecutionConflict] = Field(
        default_factory=list,
        description="List of conflicts detected during resolution (empty if valid)",
    )

    is_valid: bool = Field(
        default=True,
        description="Whether the plan is valid (no blocking conflicts, all constraints satisfied)",
    )

    def get_phase(self, phase: EnumHandlerExecutionPhase) -> ModelPhaseStep | None:
        """
        Get the phase step for a specific execution phase.

        Searches through the phases list to find a step matching the given phase.

        Args:
            phase: The execution phase to look for

        Returns:
            The ModelPhaseStep for the phase if found, None otherwise

        Example:
            >>> plan.get_phase(EnumHandlerExecutionPhase.EXECUTE)
            ModelPhaseStep(phase=<EnumHandlerExecutionPhase.EXECUTE: 'execute'>, ...)
        """
        for phase_step in self.phases:
            if phase_step.phase == phase:
                return phase_step
        return None

    def get_all_handler_ids(self) -> list[str]:
        """
        Get a flattened list of all handler IDs across all phases.

        Returns handlers in execution order (phase order, then handler order
        within each phase).

        Returns:
            List of all handler IDs in execution order

        Example:
            >>> plan.get_all_handler_ids()
            ['validate_input', 'process_data', 'transform_output']
        """
        handler_ids: list[str] = []
        for phase_step in self.phases:
            handler_ids.extend(phase_step.handler_ids)
        return handler_ids

    def total_handlers(self) -> int:
        """
        Get the total number of handlers across all phases.

        Returns:
            Total count of handlers in the execution plan

        Example:
            >>> plan.total_handlers()
            3
        """
        return sum(phase_step.handler_count() for phase_step in self.phases)

    def is_empty(self) -> bool:
        """
        Check if this execution plan has no handlers.

        An execution plan is considered empty if it has no phase steps,
        or if all phase steps have no handlers.

        Returns:
            True if the plan has no handlers, False otherwise

        Example:
            >>> empty_plan = ModelExecutionPlan()
            >>> empty_plan.is_empty()
            True
        """
        return self.total_handlers() == 0

    def has_phase(self, phase: EnumHandlerExecutionPhase) -> bool:
        """
        Check if this plan contains a specific phase.

        Args:
            phase: The execution phase to check for

        Returns:
            True if the phase exists in the plan, False otherwise
        """
        return self.get_phase(phase) is not None

    def get_phase_count(self) -> int:
        """
        Get the number of phases in this plan.

        Returns:
            Number of phase steps in the plan
        """
        return len(self.phases)

    def get_non_empty_phases(self) -> list[ModelPhaseStep]:
        """
        Get all phase steps that have at least one handler.

        Returns:
            List of phase steps with handlers
        """
        return [phase_step for phase_step in self.phases if not phase_step.is_empty()]

    # =========================================================================
    # Resolution Methods (OMN-1106)
    # =========================================================================

    def has_conflicts(self) -> bool:
        """
        Check if any conflicts were detected during resolution.

        Returns:
            True if conflicts list is non-empty.
        """
        return len(self.conflicts) > 0

    def has_blocking_conflicts(self) -> bool:
        """
        Check if any blocking (error-severity) conflicts exist.

        Blocking conflicts prevent the plan from being executed safely.

        Returns:
            True if any conflict has severity='error'.
        """
        return any(c.is_blocking() for c in self.conflicts)

    def get_blocking_conflicts(self) -> list[ModelExecutionConflict]:
        """
        Get all blocking (error-severity) conflicts.

        Returns:
            List of conflicts with severity='error'.
        """
        return [c for c in self.conflicts if c.is_blocking()]

    def get_warnings(self) -> list[ModelExecutionConflict]:
        """
        Get all warning-severity conflicts.

        Returns:
            List of conflicts with severity='warning'.
        """
        return [c for c in self.conflicts if not c.is_blocking()]

    def get_cycle_conflicts(self) -> list[ModelExecutionConflict]:
        """
        Get all cycle conflicts.

        Returns:
            List of conflicts with conflict_type='cycle'.
        """
        return [c for c in self.conflicts if c.is_cycle()]

    def had_tie_breakers(self) -> bool:
        """
        Check if any tie-breaker decisions were made during resolution.

        Returns:
            True if resolution_metadata exists and had ties.
        """
        if self.resolution_metadata is None:
            return False
        return self.resolution_metadata.had_ties()

    def can_execute(self) -> bool:
        """
        Check if this plan can be safely executed.

        A plan can be executed if:
        - is_valid is True
        - No blocking conflicts exist
        - Plan is not empty

        Returns:
            True if the plan can be executed.
        """
        return (
            self.is_valid and not self.has_blocking_conflicts() and not self.is_empty()
        )

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        phase_summaries = [
            f"{step.phase.value}({step.handler_count()})" for step in self.phases
        ]
        phases_str = " -> ".join(phase_summaries) if phase_summaries else "(empty)"
        validity = (
            "VALID" if self.is_valid else f"INVALID({len(self.conflicts)} conflicts)"
        )
        return f"ExecutionPlan[{phases_str}] {validity}"

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelExecutionPlan(phases={self.phases!r}, "
            f"source_profile={self.source_profile!r}, "
            f"ordering_policy={self.ordering_policy!r}, "
            f"created_at={self.created_at!r}, "
            f"is_valid={self.is_valid}, "
            f"conflicts={len(self.conflicts)}, "
            f"resolution_metadata={self.resolution_metadata!r})"
        )


# Export for use
__all__ = ["ModelExecutionPlan"]
