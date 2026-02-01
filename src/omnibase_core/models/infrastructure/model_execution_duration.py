"""
Execution duration model.

Duration model for execution tracking without complex dependencies.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelExecutionDuration(BaseModel):
    """Duration model for execution tracking without complex dependencies."""

    milliseconds: int = Field(default=0, ge=0, description="Duration in milliseconds")

    def total_milliseconds(self) -> int:
        """Get total duration in milliseconds."""
        return self.milliseconds

    def total_seconds(self) -> float:
        """Get total duration in seconds."""
        return self.milliseconds / 1000.0

    def __str__(self) -> str:
        """Return human-readable duration string."""
        if self.milliseconds == 0:
            return "0ms"
        if self.milliseconds < 1000:
            return f"{self.milliseconds}ms"
        if self.milliseconds < 60000:
            return f"{self.milliseconds / 1000:.1f}s"
        minutes = self.milliseconds // 60000
        seconds = (self.milliseconds % 60000) / 1000
        return f"{minutes}m{seconds:.1f}s"

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


# Export for use
__all__ = ["ModelExecutionDuration"]
