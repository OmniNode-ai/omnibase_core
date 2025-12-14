"""
Typed envelope payload model for event-driven processing.

This module provides a strongly-typed model for event envelope payloads,
replacing dict[str, str] patterns with explicit typed fields for common
event payload data including event_type, source, timestamp, and correlation_id.

The ``ModelEnvelopePayload`` class provides immutable update methods
(e.g., ``set_data()``, ``with_timestamp()``) that return new instances
to maintain data integrity in event-driven workflows.

Example:
    >>> from omnibase_core.models.common.model_envelope_payload import (
    ...     ModelEnvelopePayload,
    ... )
    >>> payload = ModelEnvelopePayload(
    ...     event_type="user.created",
    ...     source="auth-service",
    ...     correlation_id="abc-123",
    ... )
    >>> payload.event_type
    'user.created'
    >>> updated = payload.with_timestamp()  # Returns new instance
    >>> updated.timestamp is not None
    True

See Also:
    - :class:`ModelQueryParameters`: Typed query parameters for effects.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError

# Type alias for additional payload values (for data field)
PayloadDataValue = str | int | float | bool | list[str] | None


class ModelEnvelopePayload(BaseModel):
    """
    Typed envelope payload for event-driven processing.

    Replaces dict[str, str] envelope_payload field with explicit typed fields
    for common event payload data. Supports both typed common fields and
    a flexible data dictionary for event-specific attributes.

    Common Fields:
    - event_type: Type identifier for the event
    - source: Origin service or component
    - timestamp: When the event occurred (ISO 8601)
    - correlation_id: Request tracing identifier
    - data: Additional event-specific payload data

    Security:
    - String fields have max_length=512 to prevent memory exhaustion
    - Data dict has max 100 entries to prevent DoS attacks

    Example:
        >>> payload = ModelEnvelopePayload(
        ...     event_type="user.created",
        ...     source="auth-service",
        ...     correlation_id="abc-123"
        ... )
        >>> payload.event_type
        'user.created'
        >>> payload.to_dict()
        {'event_type': 'user.created', 'source': 'auth-service', ...}
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    # Security constants
    MAX_FIELD_LENGTH: ClassVar[int] = 512
    MAX_DATA_ENTRIES: ClassVar[int] = 100

    # Common event payload fields
    event_type: str | None = Field(
        default=None,
        description="Event type identifier (e.g., 'user.created', 'order.completed')",
        max_length=512,
    )
    source: str | None = Field(
        default=None,
        description="Origin service or component that generated the event",
        max_length=512,
    )
    timestamp: str | None = Field(
        default=None,
        description="ISO 8601 timestamp when the event occurred",
        max_length=64,
    )
    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for distributed request tracing",
        max_length=128,
    )

    # Flexible data container for event-specific attributes
    data: dict[str, PayloadDataValue] = Field(
        default_factory=dict,
        description="Additional event-specific payload data",
    )

    @model_validator(mode="after")
    def _validate_data_size(self) -> Self:
        """Validate data dict size to prevent DoS attacks."""
        if len(self.data) > self.MAX_DATA_ENTRIES:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Data dict exceeds maximum size of {self.MAX_DATA_ENTRIES} entries",
                data_entries=len(self.data),
                max_entries=self.MAX_DATA_ENTRIES,
            )
        return self

    @classmethod
    def from_dict(cls, data: dict[str, PayloadDataValue]) -> Self:
        """Create from a dictionary of payload data.

        Extracts known fields (event_type, source, timestamp, correlation_id)
        and places remaining fields in the data dictionary.

        Args:
            data: Dictionary of payload key-value pairs.

        Returns:
            New ModelEnvelopePayload instance.
        """
        known_fields = {"event_type", "source", "timestamp", "correlation_id"}

        # Extract typed fields
        event_type_val = data.get("event_type")
        source_val = data.get("source")
        timestamp_val = data.get("timestamp")
        correlation_id_val = data.get("correlation_id")

        # Collect unknown fields into data dict
        extra_data: dict[str, PayloadDataValue] = {}
        for key, value in data.items():
            if key not in known_fields:
                extra_data[key] = value

        return cls(
            event_type=str(event_type_val) if event_type_val is not None else None,
            source=str(source_val) if source_val is not None else None,
            timestamp=str(timestamp_val) if timestamp_val is not None else None,
            correlation_id=str(correlation_id_val)
            if correlation_id_val is not None
            else None,
            data=extra_data,
        )

    @classmethod
    def from_string_dict(cls, data: dict[str, str]) -> Self:
        """Create from a string dictionary.

        Args:
            data: Dictionary of string key-value pairs.

        Returns:
            New ModelEnvelopePayload instance.
        """
        # Convert to PayloadDataValue dict to satisfy type checker
        converted: dict[str, PayloadDataValue] = dict(data)
        return cls.from_dict(converted)

    def to_dict(self) -> dict[str, PayloadDataValue | dict[str, PayloadDataValue]]:
        """Convert to dictionary format.

        Returns:
            Dictionary representation with all fields.
        """
        result: dict[str, PayloadDataValue | dict[str, PayloadDataValue]] = {}
        if self.event_type is not None:
            result["event_type"] = self.event_type
        if self.source is not None:
            result["source"] = self.source
        if self.timestamp is not None:
            result["timestamp"] = self.timestamp
        if self.correlation_id is not None:
            result["correlation_id"] = self.correlation_id
        if self.data:
            result["data"] = self.data.copy()
        return result

    def to_string_dict(self) -> dict[str, str]:
        """Convert to dict[str, str] format.

        Flattens the structure to a simple string dictionary.

        Returns:
            Dictionary with string keys and values.
        """
        result: dict[str, str] = {}
        if self.event_type is not None:
            result["event_type"] = self.event_type
        if self.source is not None:
            result["source"] = self.source
        if self.timestamp is not None:
            result["timestamp"] = self.timestamp
        if self.correlation_id is not None:
            result["correlation_id"] = self.correlation_id
        # Flatten data items as string values
        for key, value in self.data.items():
            if value is not None:
                if isinstance(value, bool):
                    result[key] = "true" if value else "false"
                elif isinstance(value, list):
                    result[key] = ",".join(value)
                else:
                    result[key] = str(value)
        return result

    def get(self, key: str, default: PayloadDataValue = None) -> PayloadDataValue:
        """Get a payload value by key.

        Checks both typed fields and data dictionary.

        Args:
            key: Payload key to look up.
            default: Default value if key not found.

        Returns:
            Payload value or default.
        """
        # Check typed fields first
        if key == "event_type":
            return self.event_type if self.event_type is not None else default
        if key == "source":
            return self.source if self.source is not None else default
        if key == "timestamp":
            return self.timestamp if self.timestamp is not None else default
        if key == "correlation_id":
            return self.correlation_id if self.correlation_id is not None else default
        # Then check data dictionary
        return self.data.get(key, default)

    def get_data(self, key: str, default: PayloadDataValue = None) -> PayloadDataValue:
        """Get a value from the data dictionary.

        Args:
            key: Data key to look up.
            default: Default value if key not found.

        Returns:
            Data value or default.
        """
        return self.data.get(key, default)

    def set_data(self, key: str, value: PayloadDataValue) -> Self:
        """Set a value in the data dictionary, returning a new instance.

        Args:
            key: Data key to set.
            value: Value to set.

        Returns:
            New ModelEnvelopePayload instance with updated data.
        """
        new_data = self.data.copy()
        new_data[key] = value
        return self.model_copy(update={"data": new_data})

    def with_timestamp(self, timestamp: datetime | None = None) -> Self:
        """Create a new instance with updated timestamp.

        Args:
            timestamp: Timestamp to set (defaults to UTC now).

        Returns:
            New ModelEnvelopePayload instance with timestamp.
        """
        ts = timestamp or datetime.now(UTC)
        return self.model_copy(update={"timestamp": ts.isoformat()})

    def has(self, key: str) -> bool:
        """Check if a key exists in typed fields or data.

        Args:
            key: Key to check.

        Returns:
            True if key exists, False otherwise.
        """
        if key in ("event_type", "source", "timestamp", "correlation_id"):
            return getattr(self, key) is not None
        return key in self.data

    def __len__(self) -> int:
        """Return the number of non-None fields plus data items."""
        count = len(self.data)
        if self.event_type is not None:
            count += 1
        if self.source is not None:
            count += 1
        if self.timestamp is not None:
            count += 1
        if self.correlation_id is not None:
            count += 1
        return count

    def __bool__(self) -> bool:
        """Return True if there are any payload items."""
        return (
            self.event_type is not None
            or self.source is not None
            or self.timestamp is not None
            or self.correlation_id is not None
            or bool(self.data)
        )

    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        return self.has(key)


__all__ = ["ModelEnvelopePayload", "PayloadDataValue"]
