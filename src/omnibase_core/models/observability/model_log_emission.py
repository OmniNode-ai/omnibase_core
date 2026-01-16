"""Log emission model for observability."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_severity import EnumSeverity


class ModelLogEmission(BaseModel):
    """Represents a structured log emission event.

    Provides a standardized format for log entries with severity,
    message, structured context, and timestamp.

    Attributes:
        level: Severity level of the log entry.
        message: Human-readable log message.
        context: Structured key-value context for the log entry.
        timestamp: When the log event occurred (defaults to now).
    """

    level: EnumSeverity = Field(
        default=EnumSeverity.INFO,
        description="Log severity level",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=8192,
        description="Log message",
    )
    context: dict[str, str] = Field(
        default_factory=dict,
        description="Structured context as string key-value pairs",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of the log event (UTC)",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


__all__ = ["ModelLogEmission"]
