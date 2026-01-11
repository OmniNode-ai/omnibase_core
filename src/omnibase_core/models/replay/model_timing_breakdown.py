"""Model for detailed timing breakdown."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.replay.model_phase_time import ModelPhaseTime


class ModelTimingBreakdown(BaseModel):
    """Detailed timing breakdown.

    Captures total execution timing for baseline and replay,
    with delta calculations and optional per-phase breakdown.

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    baseline_total_ms: float
    replay_total_ms: float
    delta_ms: float
    delta_percent: float

    # Phase breakdown if available
    phases: list[ModelPhaseTime] | None = None


__all__ = ["ModelTimingBreakdown"]
