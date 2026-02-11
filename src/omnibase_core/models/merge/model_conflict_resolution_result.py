"""
Conflict Resolution Result Model for Geometric Conflict Tracking.

This module defines ModelConflictResolutionResult, which tracks how a
geometric conflict was resolved, including whether human approval was
required and obtained.

Global Invariant GI-3:
    OPPOSITE and AMBIGUOUS conflicts MUST have required_human_approval=True.
    This is enforced at construction time via a model validator.

See Also:
    - OMN-1853: ModelConflictResolutionResult implementation
    - ModelGeometricConflictDetails: The conflict analysis that was resolved

.. versionadded:: 0.16.1
    Added as part of geometric conflict analysis (OMN-1853)
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.merge.model_geometric_conflict_details import (
    HUMAN_APPROVAL_REQUIRED_TYPES,
    ModelGeometricConflictDetails,
)


class ModelConflictResolutionResult(BaseModel):
    """
    Tracks how a geometric conflict was resolved.

    Enforces GI-3: OPPOSITE and AMBIGUOUS conflicts must have
    required_human_approval=True. This is validated at construction time.

    Thread Safety:
        Immutable (frozen=True) and safe for concurrent access.

    .. versionadded:: 0.16.1
        Added as part of geometric conflict analysis (OMN-1853)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    details: ModelGeometricConflictDetails = Field(
        ...,
        description="The conflict analysis that was resolved",
    )

    resolved_value: Any = Field(
        ...,
        description=(
            "The final resolved value. Callers must not mutate this value "
            "in-place; frozen=True prevents reassignment but not deep mutation "
            "of mutable payloads."
        ),
    )

    resolution_strategy: str = Field(
        ...,
        min_length=1,
        description="Strategy used to resolve (e.g., 'pick_best', 'merge', 'human_decision')",
    )

    required_human_approval: bool = Field(
        ...,
        description="Whether human approval was required for this resolution",
    )

    human_approved: bool = Field(
        default=False,
        description="Whether a human has approved this resolution",
    )

    @model_validator(mode="after")
    def _enforce_gi3_human_approval(self) -> "ModelConflictResolutionResult":
        """GI-3: OPPOSITE and AMBIGUOUS must require human approval."""
        if (
            self.details.conflict_type in HUMAN_APPROVAL_REQUIRED_TYPES
            and not self.required_human_approval
        ):
            msg = (
                f"GI-3 violation: conflict_type={self.details.conflict_type.value} "
                f"requires human approval but required_human_approval=False"
            )
            raise ValueError(msg)
        return self

    def __str__(self) -> str:
        approval = "approved" if self.human_approved else "pending"
        if not self.required_human_approval:
            approval = "auto"
        return f"Resolution({self.resolution_strategy}, approval={approval})"

    def __repr__(self) -> str:
        return (
            f"ModelConflictResolutionResult("
            f"strategy={self.resolution_strategy!r}, "
            f"required_human_approval={self.required_human_approval}, "
            f"human_approved={self.human_approved})"
        )


__all__ = [
    "ModelConflictResolutionResult",
]
