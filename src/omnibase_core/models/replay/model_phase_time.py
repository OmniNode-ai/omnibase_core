"""Model for timing of a specific execution phase."""

from pydantic import BaseModel, ConfigDict


class ModelPhaseTime(BaseModel):
    """Timing for a specific phase of execution.

    Captures timing metrics for individual phases within an execution,
    comparing baseline vs replay performance.

    Attributes:
        phase_name: Name identifier for this execution phase.
        baseline_ms: Baseline execution time in milliseconds.
        replay_ms: Replay execution time in milliseconds.
        delta_percent: Percentage difference between replay and baseline.

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    phase_name: str
    baseline_ms: float
    replay_ms: float
    delta_percent: float


__all__ = ["ModelPhaseTime"]
