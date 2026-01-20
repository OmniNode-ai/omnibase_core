"""Model for demo run configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDemoConfig(BaseModel):
    """Configuration used for the demo run.

    Captures the parameters that were used to execute the demo scenario
    for reproducibility and debugging.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    scenario: str = Field(..., description="Name of the demo scenario executed")
    live: bool = Field(..., description="Whether live LLM calls were made")
    seed: int | None = Field(
        default=None, description="Random seed for reproducibility"
    )
    repeat: int = Field(..., ge=1, description="Number of times to repeat the demo")
    timestamp: str = Field(..., description="ISO-8601 timestamp of the run")


__all__ = ["ModelDemoConfig"]
