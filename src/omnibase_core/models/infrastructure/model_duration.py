"""
Duration Model.

A duration model that delegates to ModelTimeBased for unified time handling.
Provides convenient methods for working with time durations in various units.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ...enums.enum_time_unit import EnumTimeUnit
from .model_time_based import ModelTimeBased


class ModelDuration(BaseModel):
    """
    Duration model that provides convenient methods for time duration handling.

    This model delegates all operations to the unified ModelTimeBased model
    while providing an intuitive interface for duration operations.
    """

    time_based: ModelTimeBased[int] = Field(
        default_factory=lambda: ModelTimeBased(value=0, unit=EnumTimeUnit.MILLISECONDS),
        exclude=True,
        description="Internal time-based model",
    )

    def __init__(self, **data: Any) -> None:
        """Initialize duration with flexible input formats."""
        # Handle various input formats
        if "milliseconds" in data:
            ms = data.pop("milliseconds")
            super().__init__()
            self.time_based = ModelTimeBased(value=ms, unit=EnumTimeUnit.MILLISECONDS)
        elif "seconds" in data:
            seconds = data.pop("seconds")
            super().__init__()
            self.time_based = ModelTimeBased(
                value=int(seconds * 1000),
                unit=EnumTimeUnit.MILLISECONDS,
            )
        elif "minutes" in data:
            minutes = data.pop("minutes")
            super().__init__()
            self.time_based = ModelTimeBased(
                value=int(minutes * 60 * 1000),
                unit=EnumTimeUnit.MILLISECONDS,
            )
        elif "hours" in data:
            hours = data.pop("hours")
            super().__init__()
            self.time_based = ModelTimeBased(
                value=int(hours * 60 * 60 * 1000),
                unit=EnumTimeUnit.MILLISECONDS,
            )
        elif "days" in data:
            days = data.pop("days")
            super().__init__()
            self.time_based = ModelTimeBased(
                value=int(days * 24 * 60 * 60 * 1000),
                unit=EnumTimeUnit.MILLISECONDS,
            )
        else:
            super().__init__(**data)

    @property
    def milliseconds(self) -> int:
        """Get duration in milliseconds."""
        return self.time_based.to_milliseconds()

    def total_milliseconds(self) -> int:
        """Get total duration in milliseconds."""
        return self.time_based.to_milliseconds()

    def total_seconds(self) -> float:
        """Get total duration in seconds."""
        return self.time_based.to_seconds()

    def total_minutes(self) -> float:
        """Get total duration in minutes."""
        return self.time_based.to_minutes()

    def total_hours(self) -> float:
        """Get total duration in hours."""
        return self.time_based.to_hours()

    def total_days(self) -> float:
        """Get total duration in days."""
        return self.time_based.to_days()

    def is_zero(self) -> bool:
        """Check if duration is zero."""
        return self.time_based.is_zero()

    def is_positive(self) -> bool:
        """Check if duration is positive."""
        return self.time_based.is_positive()

    def __str__(self) -> str:
        """Return human-readable duration string."""
        return str(self.time_based)

    @classmethod
    def from_milliseconds(cls, ms: int) -> ModelDuration:
        """Create duration from milliseconds."""
        instance = cls()
        instance.time_based = ModelTimeBased(value=ms, unit=EnumTimeUnit.MILLISECONDS)
        return instance

    @classmethod
    def from_seconds(cls, seconds: float) -> ModelDuration:
        """Create duration from seconds."""
        instance = cls()
        instance.time_based = ModelTimeBased(
            value=int(seconds * 1000),
            unit=EnumTimeUnit.MILLISECONDS,
        )
        return instance

    @classmethod
    def from_minutes(cls, minutes: float) -> ModelDuration:
        """Create duration from minutes."""
        instance = cls()
        instance.time_based = ModelTimeBased(
            value=int(minutes * 60 * 1000),
            unit=EnumTimeUnit.MILLISECONDS,
        )
        return instance

    @classmethod
    def from_hours(cls, hours: float) -> ModelDuration:
        """Create duration from hours."""
        instance = cls()
        instance.time_based = ModelTimeBased(
            value=int(hours * 60 * 60 * 1000),
            unit=EnumTimeUnit.MILLISECONDS,
        )
        return instance

    @classmethod
    def zero(cls) -> ModelDuration:
        """Create zero duration."""
        instance = cls()
        instance.time_based = ModelTimeBased.zero()
        return instance

    def get_time_based(self) -> ModelTimeBased[int]:
        """Get the underlying time-based model."""
        return self.time_based

    def model_dump(self, **kwargs: Any) -> dict[str, int]:
        """Serialize model with typed return."""
        return {"milliseconds": self.milliseconds}


# Export for use
__all__ = ["ModelDuration"]
