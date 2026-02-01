"""Model for detailed timing breakdown."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.replay.model_phase_time import ModelPhaseTime

# Tolerance for floating-point comparisons (0.01ms for delta_ms, 0.01% for delta_percent)
_DELTA_MS_TOLERANCE = 0.01
_DELTA_PERCENT_TOLERANCE = 0.01


class ModelTimingBreakdown(BaseModel):
    """Detailed timing breakdown.

    Captures total execution timing for baseline and replay,
    with delta calculations and optional per-phase breakdown.

    Example:
        A timing breakdown showing 50% slower replay execution::

            >>> breakdown = ModelTimingBreakdown(
            ...     baseline_total_ms=100.0,
            ...     replay_total_ms=150.0,
            ...     delta_ms=50.0,        # 150 - 100 = 50ms slower
            ...     delta_percent=50.0,   # (50 / 100) * 100 = 50% slower
            ...     phases=[
            ...         ModelPhaseTime(
            ...             phase_name="initialization",
            ...             baseline_ms=20.0,
            ...             replay_ms=25.0,
            ...             delta_percent=25.0
            ...         ),
            ...         ModelPhaseTime(
            ...             phase_name="computation",
            ...             baseline_ms=80.0,
            ...             replay_ms=125.0,
            ...             delta_percent=56.25
            ...         ),
            ...     ]
            ... )

        Interpretation:
            - delta_ms > 0: Replay is slower than baseline
            - delta_ms < 0: Replay is faster than baseline
            - delta_percent = 50.0: Replay took 50% more time
            - delta_percent = -25.0: Replay took 25% less time

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    Validation:
        - baseline_total_ms: Must be non-negative (>= 0)
        - replay_total_ms: Must be non-negative (>= 0)
        - delta_ms: Must equal (replay_total_ms - baseline_total_ms) within tolerance
        - delta_percent: Must equal (delta_ms / baseline_total_ms) * 100 within tolerance
          when baseline_total_ms > 0. When baseline_total_ms == 0, delta_percent validation
          is skipped (percentage change from zero is undefined).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    baseline_total_ms: float = Field(ge=0, description="Baseline execution time in ms")
    replay_total_ms: float = Field(ge=0, description="Replay execution time in ms")
    delta_ms: float = Field(description="Time difference (replay - baseline) in ms")
    delta_percent: float = Field(description="Percentage change from baseline")

    # Phase breakdown if available
    phases: list[ModelPhaseTime] | None = None

    @model_validator(mode="after")
    def validate_delta_consistency(self) -> Self:
        """Validate that delta values are mathematically consistent.

        Raises:
            ValueError: If delta_ms does not match (replay_total_ms - baseline_total_ms)
                within tolerance, or if delta_percent is inconsistent when baseline > 0.
        """
        expected_delta_ms = self.replay_total_ms - self.baseline_total_ms

        if abs(self.delta_ms - expected_delta_ms) > _DELTA_MS_TOLERANCE:
            raise ValueError(
                f"delta_ms ({self.delta_ms}) is inconsistent with "
                f"replay_total_ms ({self.replay_total_ms}) - baseline_total_ms "
                f"({self.baseline_total_ms}). Expected: {expected_delta_ms}"
            )

        # Only validate delta_percent when baseline > 0
        # Percentage change from zero is mathematically undefined
        if self.baseline_total_ms > 0:
            expected_delta_percent = (self.delta_ms / self.baseline_total_ms) * 100

            if (
                abs(self.delta_percent - expected_delta_percent)
                > _DELTA_PERCENT_TOLERANCE
            ):
                raise ValueError(
                    f"delta_percent ({self.delta_percent}) is inconsistent with "
                    f"(delta_ms / baseline_total_ms) * 100. "
                    f"Expected: {expected_delta_percent}"
                )

        return self


__all__ = ["ModelTimingBreakdown"]
