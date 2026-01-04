"""Summary model for invariant comparison between baseline and replay.

Thread Safety:
    ModelInvariantComparisonSummary is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelInvariantComparisonSummary(BaseModel):
    """Summary of invariant comparison between baseline and replay.

    Aggregates statistics about how invariant evaluations changed between
    a baseline execution and a replay execution.

    Attributes:
        total_invariants: Total number of invariants compared.
        both_passed: Number of invariants that passed in both baseline and replay.
        both_failed: Number of invariants that failed in both baseline and replay.
        new_violations: Invariants that passed baseline but failed replay (REGRESSION).
        fixed_violations: Invariants that failed baseline but passed replay (IMPROVEMENT).
        regression_detected: True if any new violations were detected.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    total_invariants: int = Field(
        ...,
        ge=0,
        description="Total number of invariants compared",
    )
    both_passed: int = Field(
        ...,
        ge=0,
        description="Number of invariants that passed in both baseline and replay",
    )
    both_failed: int = Field(
        ...,
        ge=0,
        description="Number of invariants that failed in both baseline and replay",
    )
    new_violations: int = Field(
        ...,
        ge=0,
        description="Invariants that passed baseline but failed replay (REGRESSION)",
    )
    fixed_violations: int = Field(
        ...,
        ge=0,
        description="Invariants that failed baseline but passed replay (IMPROVEMENT)",
    )
    regression_detected: bool = Field(
        ...,
        description="True if any new violations were detected (new_violations > 0)",
    )


__all__ = ["ModelInvariantComparisonSummary"]
