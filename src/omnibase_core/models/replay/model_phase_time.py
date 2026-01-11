"""Model for timing of a specific execution phase."""

from pydantic import BaseModel, ConfigDict


class ModelPhaseTime(BaseModel):
    """Timing for a specific phase of execution.

    Captures timing metrics for individual phases within an execution,
    comparing baseline vs replay performance.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    phase_name: str
    baseline_ms: float
    replay_ms: float
    delta_percent: float


__all__ = ["ModelPhaseTime"]
