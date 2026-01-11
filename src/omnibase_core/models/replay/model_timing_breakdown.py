"""Model for detailed timing breakdown."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.replay.model_phase_time import ModelPhaseTime


class ModelTimingBreakdown(BaseModel):
    """Detailed timing breakdown.

    Captures total execution timing for baseline and replay,
    with delta calculations and optional per-phase breakdown.

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    Validation:
        - baseline_total_ms: Must be non-negative (>= 0)
        - replay_total_ms: Must be non-negative (>= 0)
        - delta_ms: Can be negative (replay faster than baseline)
        - delta_percent: Can be negative (replay faster than baseline)
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    baseline_total_ms: float = Field(ge=0, description="Baseline execution time in ms")
    replay_total_ms: float = Field(ge=0, description="Replay execution time in ms")
    delta_ms: float = Field(description="Time difference (replay - baseline) in ms")
    delta_percent: float = Field(description="Percentage change from baseline")

    # Phase breakdown if available
    phases: list[ModelPhaseTime] | None = None


__all__ = ["ModelTimingBreakdown"]
