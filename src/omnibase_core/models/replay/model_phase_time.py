"""Model for timing of a specific execution phase."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Tolerance for floating-point comparisons (0.01% for delta_percent)
_DELTA_PERCENT_TOLERANCE = 0.01


class ModelPhaseTime(BaseModel):
    """Timing for a specific phase of execution.

    Captures timing metrics for individual phases within an execution,
    comparing baseline vs replay performance.

    Example:
        A phase that took 25% longer in replay::

            >>> phase = ModelPhaseTime(
            ...     phase_name="data_processing",
            ...     baseline_ms=80.0,
            ...     replay_ms=100.0,
            ...     delta_percent=25.0  # ((100 - 80) / 80) * 100 = 25%
            ... )

        A phase that was 20% faster in replay::

            >>> phase = ModelPhaseTime(
            ...     phase_name="initialization",
            ...     baseline_ms=50.0,
            ...     replay_ms=40.0,
            ...     delta_percent=-20.0  # ((40 - 50) / 50) * 100 = -20%
            ... )

        Interpretation:
            - delta_percent > 0: Phase is slower in replay
            - delta_percent < 0: Phase is faster in replay
            - delta_percent = 0: No timing difference

    Attributes:
        phase_name: Name identifier for this execution phase.
        baseline_ms: Baseline execution time in milliseconds.
        replay_ms: Replay execution time in milliseconds.
        delta_percent: Percentage difference between replay and baseline.

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    Validation:
        - phase_name: Must be non-empty (min_length=1)
        - baseline_ms: Must be non-negative (>= 0)
        - replay_ms: Must be non-negative (>= 0)
        - delta_percent: Must equal ((replay_ms - baseline_ms) / baseline_ms) * 100
          within tolerance when baseline_ms > 0. When baseline_ms == 0,
          delta_percent validation is skipped (percentage change from zero is undefined).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    phase_name: str = Field(
        min_length=1, description="Name identifier for this execution phase"
    )
    baseline_ms: float = Field(
        ge=0, description="Baseline execution time in milliseconds"
    )
    replay_ms: float = Field(ge=0, description="Replay execution time in milliseconds")
    delta_percent: float = Field(
        description="Percentage difference between replay and baseline"
    )

    @model_validator(mode="after")
    def validate_delta_consistency(self) -> Self:
        """Validate that delta_percent is mathematically consistent.

        Raises:
            ValueError: If delta_percent does not match
                ((replay_ms - baseline_ms) / baseline_ms) * 100 within tolerance
                when baseline_ms > 0.
        """
        # Only validate delta_percent when baseline > 0
        # Percentage change from zero is mathematically undefined
        if self.baseline_ms > 0:
            expected_delta_percent = (
                (self.replay_ms - self.baseline_ms) / self.baseline_ms
            ) * 100

            if (
                abs(self.delta_percent - expected_delta_percent)
                > _DELTA_PERCENT_TOLERANCE
            ):
                raise ValueError(
                    f"delta_percent ({self.delta_percent}) is inconsistent with "
                    f"((replay_ms - baseline_ms) / baseline_ms) * 100. "
                    f"Expected: {expected_delta_percent}"
                )

        return self


__all__ = ["ModelPhaseTime"]
