"""Summary model for invariant comparison between baseline and replay.

Thread Safety:
    ModelInvariantComparisonSummary is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


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
        regression_detected: Computed property, True if new_violations > 0.

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

    @model_validator(mode="after")
    def validate_counts_sum_to_total(self) -> "ModelInvariantComparisonSummary":
        """Validate that the sum of all category counts equals total_invariants.

        Ensures data consistency by verifying:
        both_passed + both_failed + new_violations + fixed_violations == total_invariants
        """
        computed_sum = (
            self.both_passed
            + self.both_failed
            + self.new_violations
            + self.fixed_violations
        )
        if computed_sum != self.total_invariants:
            raise ValueError(
                f"Sum of counts ({computed_sum}) does not equal total_invariants "
                f"({self.total_invariants}). Expected: both_passed ({self.both_passed}) + "
                f"both_failed ({self.both_failed}) + new_violations ({self.new_violations}) + "
                f"fixed_violations ({self.fixed_violations}) = {self.total_invariants}"
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def regression_detected(self) -> bool:
        """Return True if any new violations were detected."""
        return self.new_violations > 0


__all__ = ["ModelInvariantComparisonSummary"]
