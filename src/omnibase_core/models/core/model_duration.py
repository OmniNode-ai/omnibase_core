"""
Duration model for time tracking.
"""

from pydantic import BaseModel, Field


class ModelDuration(BaseModel):
    """Duration representation for time tracking."""

    milliseconds: int = Field(
        default=0,
        description="Duration in milliseconds",
        ge=0,
    )

    def total_milliseconds(self) -> int:
        """Get total duration in milliseconds."""
        return self.milliseconds

    def total_seconds(self) -> float:
        """Get total duration in seconds."""
        return self.milliseconds / 1000.0

    def total_minutes(self) -> float:
        """Get total duration in minutes."""
        return self.total_seconds() / 60.0

    @classmethod
    def from_milliseconds(cls, ms: int) -> "ModelDuration":
        """Create duration from milliseconds."""
        return cls(milliseconds=ms)

    @classmethod
    def from_seconds(cls, seconds: float) -> "ModelDuration":
        """Create duration from seconds."""
        return cls(milliseconds=int(seconds * 1000))

    def __str__(self) -> str:
        """String representation of duration."""
        if self.milliseconds < 1000:
            return f"{self.milliseconds}ms"
        if self.total_seconds() < 60:
            return f"{self.total_seconds():.2f}s"
        return f"{self.total_minutes():.2f}min"
