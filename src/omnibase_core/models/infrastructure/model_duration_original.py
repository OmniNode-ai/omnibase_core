"""
Duration Model

Type-safe duration representation with multiple time units
and conversion capabilities. Enhanced with archived features.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError


class ModelDuration(BaseModel):
    """
    Type-safe duration representation.

    This model provides a structured way to represent time durations
    with automatic conversion between different time units.
    """

    milliseconds: int = Field(default=0, description="Duration in milliseconds", ge=0)

    def __init__(self, **data: Any) -> None:
        """Initialize duration with flexible input."""
        # Handle different input formats
        if "seconds" in data:
            data["milliseconds"] = int(data.pop("seconds") * 1000)
        elif "minutes" in data:
            data["milliseconds"] = int(data.pop("minutes") * 60 * 1000)
        elif "hours" in data:
            data["milliseconds"] = int(data.pop("hours") * 60 * 60 * 1000)
        elif "days" in data:
            data["milliseconds"] = int(data.pop("days") * 24 * 60 * 60 * 1000)

        super().__init__(**data)

    @field_validator("milliseconds")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        """Ensure duration is non-negative."""
        if v < 0:
            msg = "Duration must be non-negative"
            raise OnexError(code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg)
        return v

    def total_milliseconds(self) -> int:
        """Get total duration in milliseconds."""
        return self.milliseconds

    def total_seconds(self) -> float:
        """Get total duration in seconds."""
        return self.milliseconds / 1000.0

    def total_minutes(self) -> float:
        """Get total duration in minutes."""
        return self.milliseconds / (1000.0 * 60)

    def total_hours(self) -> float:
        """Get total duration in hours."""
        return self.milliseconds / (1000.0 * 60 * 60)

    def total_days(self) -> float:
        """Get total duration in days."""
        return self.milliseconds / (1000.0 * 60 * 60 * 24)

    def is_zero(self) -> bool:
        """Check if duration is zero."""
        return self.milliseconds == 0

    def is_positive(self) -> bool:
        """Check if duration is positive."""
        return self.milliseconds > 0

    def __str__(self) -> str:
        """Return human-readable duration string."""
        if self.milliseconds == 0:
            return "0ms"

        parts = []
        remaining_ms = self.milliseconds

        # Days
        days = remaining_ms // (24 * 60 * 60 * 1000)
        if days > 0:
            parts.append(f"{days}d")
            remaining_ms %= 24 * 60 * 60 * 1000

        # Hours
        hours = remaining_ms // (60 * 60 * 1000)
        if hours > 0:
            parts.append(f"{hours}h")
            remaining_ms %= 60 * 60 * 1000

        # Minutes
        minutes = remaining_ms // (60 * 1000)
        if minutes > 0:
            parts.append(f"{minutes}m")
            remaining_ms %= 60 * 1000

        # Seconds
        seconds = remaining_ms // 1000
        if seconds > 0:
            parts.append(f"{seconds}s")
            remaining_ms %= 1000

        # Milliseconds
        if remaining_ms > 0:
            parts.append(f"{remaining_ms}ms")

        return "".join(parts)

    @classmethod
    def from_milliseconds(cls, ms: int) -> ModelDuration:
        """Create duration from milliseconds."""
        return cls(milliseconds=ms)

    @classmethod
    def from_seconds(cls, seconds: float) -> ModelDuration:
        """Create duration from seconds."""
        return cls(milliseconds=int(seconds * 1000))

    @classmethod
    def from_minutes(cls, minutes: float) -> ModelDuration:
        """Create duration from minutes."""
        return cls(milliseconds=int(minutes * 60 * 1000))

    @classmethod
    def from_hours(cls, hours: float) -> ModelDuration:
        """Create duration from hours."""
        return cls(milliseconds=int(hours * 60 * 60 * 1000))

    @classmethod
    def zero(cls) -> ModelDuration:
        """Create zero duration."""
        return cls(milliseconds=0)
