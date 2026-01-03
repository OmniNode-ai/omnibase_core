"""
Model for FSM semantic analysis results.

Contains all detected semantic issues across multiple validation categories.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.models.validation.model_ambiguous_transition import (
    ModelAmbiguousTransition,
)


class ModelFSMAnalysisResult(BaseModel):
    """
    Comprehensive FSM semantic analysis result.

    Contains all detected semantic issues across multiple validation categories.
    The is_valid computed property returns True only if NO issues are detected
    across all categories.

    This model is immutable (frozen=True) and returns all issues without raising
    exceptions, allowing callers to inspect and handle issues programmatically.

    Attributes:
        unreachable_states: States that can never be reached from initial state
        cycles_without_exit: Cycles with no path to terminal states (infinite loops)
        ambiguous_transitions: Same trigger from same state → multiple targets
        dead_transitions: Transitions that can never fire due to conditions
        missing_transitions: Non-terminal states with no outgoing transitions
        duplicate_state_names: State names that appear multiple times in FSM
        errors: Human-readable error messages for all detected issues
        is_valid: Computed property - True if no issues detected
    """

    unreachable_states: list[str] = Field(
        default_factory=list,
        description="States that cannot be reached from the initial state",
    )

    cycles_without_exit: list[list[str]] = Field(
        default_factory=list,
        description=(
            "Cycles (loops) that have no path to terminal states. "
            "Each cycle is a list of state names forming the loop."
        ),
    )

    ambiguous_transitions: list[ModelAmbiguousTransition] = Field(
        default_factory=list,
        description=(
            "Transitions where the same trigger from the same state "
            "leads to multiple possible target states"
        ),
    )

    dead_transitions: list[str] = Field(
        default_factory=list,
        description=(
            "Transition names that can never fire due to impossible "
            "conditions or unreachable source states"
        ),
    )

    missing_transitions: list[str] = Field(
        default_factory=list,
        description=(
            "Non-terminal states that have no outgoing transitions. "
            "These states will trap the FSM with no way to progress."
        ),
    )

    duplicate_state_names: list[str] = Field(
        default_factory=list,
        description="State names that appear multiple times in the FSM definition",
    )

    errors: list[str] = Field(
        default_factory=list,
        description="Human-readable error messages for all detected issues",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_valid(self) -> bool:
        """
        Returns True if no semantic issues were detected across all categories.

        An FSM is considered valid if:
        - All states are reachable from initial state
        - No cycles exist without exit paths
        - No transitions are ambiguous
        - No transitions are dead/unreachable
        - All non-terminal states have outgoing transitions
        - No duplicate state names exist

        Returns:
            True if FSM has no semantic issues, False otherwise
        """
        return (
            len(self.unreachable_states) == 0
            and len(self.cycles_without_exit) == 0
            and len(self.ambiguous_transitions) == 0
            and len(self.dead_transitions) == 0
            and len(self.missing_transitions) == 0
            and len(self.duplicate_state_names) == 0
        )

    model_config = ConfigDict(
        frozen=True,  # Immutable after creation
        extra="forbid",  # No extra fields allowed
        from_attributes=True,  # pytest-xdist compatibility
    )


__all__ = ["ModelFSMAnalysisResult"]
