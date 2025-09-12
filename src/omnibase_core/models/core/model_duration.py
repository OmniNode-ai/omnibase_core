"""
Duration Model

Type-safe duration representation with multiple time units
and conversion capabilities.
"""

from pydantic import BaseModel, Field, field_validator


class ModelDuration(BaseModel):
    """
    Type-safe duration representation.

    This model provides a structured way to represent time durations
    with automatic conversion between different time units.
    """

    milliseconds: int = Field(default=0, description="Duration in milliseconds", ge=0)

    def __init__(self, **data):
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
    def validate_positive(cls, v):
        """Ensure duration is non-negative."""
        if v < 0:
            msg = "Duration must be non-negative"
            raise ValueError(msg)
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

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"ModelDuration(milliseconds={self.milliseconds})"

    def __eq__(self, other) -> bool:
        """Check equality with another duration."""
        if isinstance(other, ModelDuration):
            return self.milliseconds == other.milliseconds
        return False

    def __lt__(self, other) -> bool:
        """Check if this duration is less than another."""
        if isinstance(other, ModelDuration):
            return self.milliseconds < other.milliseconds
        msg = f"Cannot compare ModelDuration with {type(other)}"
        raise TypeError(msg)

    def __le__(self, other) -> bool:
        """Check if this duration is less than or equal to another."""
        if isinstance(other, ModelDuration):
            return self.milliseconds <= other.milliseconds
        msg = f"Cannot compare ModelDuration with {type(other)}"
        raise TypeError(msg)

    def __gt__(self, other) -> bool:
        """Check if this duration is greater than another."""
        if isinstance(other, ModelDuration):
            return self.milliseconds > other.milliseconds
        msg = f"Cannot compare ModelDuration with {type(other)}"
        raise TypeError(msg)

    def __ge__(self, other) -> bool:
        """Check if this duration is greater than or equal to another."""
        if isinstance(other, ModelDuration):
            return self.milliseconds >= other.milliseconds
        msg = f"Cannot compare ModelDuration with {type(other)}"
        raise TypeError(msg)

    def __add__(self, other) -> "ModelDuration":
        """Add two durations."""
        if isinstance(other, ModelDuration):
            return ModelDuration(milliseconds=self.milliseconds + other.milliseconds)
        msg = f"Cannot add ModelDuration with {type(other)}"
        raise TypeError(msg)

    def __sub__(self, other) -> "ModelDuration":
        """Subtract two durations."""
        if isinstance(other, ModelDuration):
            result_ms = max(0, self.milliseconds - other.milliseconds)
            return ModelDuration(milliseconds=result_ms)
        msg = f"Cannot subtract {type(other)} from ModelDuration"
        raise TypeError(msg)

    def __mul__(self, other) -> "ModelDuration":
        """Multiply duration by a number."""
        if isinstance(other, int | float):
            return ModelDuration(milliseconds=int(self.milliseconds * other))
        msg = f"Cannot multiply ModelDuration with {type(other)}"
        raise TypeError(msg)

    def __truediv__(self, other) -> "ModelDuration":
        """Divide duration by a number."""
        if isinstance(other, int | float):
            if other == 0:
                msg = "Cannot divide duration by zero"
                raise ZeroDivisionError(msg)
            return ModelDuration(milliseconds=int(self.milliseconds / other))
        msg = f"Cannot divide ModelDuration by {type(other)}"
        raise TypeError(msg)

    @classmethod
    def from_seconds(cls, seconds: float) -> "ModelDuration":
        """Create duration from seconds."""
        return cls(milliseconds=int(seconds * 1000))

    @classmethod
    def from_minutes(cls, minutes: float) -> "ModelDuration":
        """Create duration from minutes."""
        return cls(milliseconds=int(minutes * 60 * 1000))

    @classmethod
    def from_hours(cls, hours: float) -> "ModelDuration":
        """Create duration from hours."""
        return cls(milliseconds=int(hours * 60 * 60 * 1000))

    @classmethod
    def from_days(cls, days: float) -> "ModelDuration":
        """Create duration from days."""
        return cls(milliseconds=int(days * 24 * 60 * 60 * 1000))

    @classmethod
    def zero(cls) -> "ModelDuration":
        """Create zero duration."""
        return cls(milliseconds=0)

    @classmethod
    def parse(cls, duration_str: str) -> "ModelDuration":
        """
        Parse duration from string format.

        Supports formats like: "5s", "10m", "2h", "1d", "500ms", "1h30m"
        """
        import re

        if not duration_str or duration_str.strip() == "":
            return cls.zero()

        # Remove whitespace
        duration_str = duration_str.replace(" ", "")

        # Pattern to match duration components
        pattern = r"(\d+(?:\.\d+)?)(ms|s|m|h|d)"
        matches = re.findall(pattern, duration_str.lower())

        if not matches:
            msg = f"Invalid duration format: {duration_str}"
            raise ValueError(msg)

        total_ms = 0
        for value_str, unit in matches:
            value = float(value_str)

            if unit == "ms":
                total_ms += int(value)
            elif unit == "s":
                total_ms += int(value * 1000)
            elif unit == "m":
                total_ms += int(value * 60 * 1000)
            elif unit == "h":
                total_ms += int(value * 60 * 60 * 1000)
            elif unit == "d":
                total_ms += int(value * 24 * 60 * 60 * 1000)

        return cls(milliseconds=total_ms)
