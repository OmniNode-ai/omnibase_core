"""
Typed envelope payload model for event-driven processing.

This module provides a strongly-typed model for event envelope payloads,
replacing dict[str, str] patterns with explicit typed fields for common
event payload data including event_type, source, timestamp, and correlation_id.

The ``ModelEnvelopePayload`` class provides immutable update methods
(e.g., ``set_data()``, ``with_timestamp()``) that return new instances
to maintain data integrity in event-driven workflows.

Timezone Handling:
    The ``timestamp`` field uses ``str`` type (not ``datetime``) because this model
    is designed for serialization to string dictionaries (HTTP headers, query params).

    To set a UTC timestamp, use the ``with_timestamp()`` method which:
    1. Accepts an optional ``datetime`` object (defaults to UTC now)
    2. Converts to ISO 8601 format with timezone information
    3. Returns a new immutable instance

    This differs from runtime event models (``ModelRuntimeEventBase`` and subclasses)
    which use ``datetime`` type directly for internal processing and elapsed time
    calculations. The string format here ensures compatibility with HTTP transport
    and external system integration.

    Example:
        >>> payload = ModelEnvelopePayload(event_type="user.created")
        >>> payload = payload.with_timestamp()  # Sets ISO 8601 UTC timestamp
        >>> payload.timestamp
        '2024-01-15T10:30:00+00:00'

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
    - :class:`ModelRuntimeEventBase`: Base class using datetime type for runtime events.
"""

from __future__ import annotations

import warnings
from datetime import UTC, datetime
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.types.model_onex_common_types import CliValue


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
    - Reserved keys in data dict are prefixed with "data_" to prevent collision

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

    model_config = ConfigDict(
        extra="forbid", from_attributes=True, validate_assignment=True
    )

    # Security constants
    MAX_FIELD_LENGTH: ClassVar[int] = 512
    MAX_DATA_ENTRIES: ClassVar[int] = 100

    # Reserved keys that cannot be used in data dict (would collide with typed fields)
    RESERVED_KEYS: ClassVar[frozenset[str]] = frozenset(
        {"event_type", "source", "timestamp", "correlation_id", "data"}
    )

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
    # NOTE: Uses str type (not datetime) for HTTP transport compatibility.
    # Use with_timestamp() to set a UTC timestamp in ISO 8601 format.
    # See module docstring "Timezone Handling" section for rationale.
    timestamp: str | None = Field(
        default=None,
        description="ISO 8601 timestamp with timezone (e.g., '2024-01-15T10:30:00+00:00')",
        max_length=64,
    )
    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for distributed request tracing",
        max_length=128,
    )

    # Flexible data container for event-specific attributes
    data: dict[str, CliValue | None] = Field(
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
    def from_dict(
        cls, data: dict[str, CliValue | None | dict[str, CliValue | None]]
    ) -> Self:
        """Create from a dictionary of payload data.

        Extracts known fields (event_type, source, timestamp, correlation_id)
        and places remaining fields in the data dictionary.

        Handles round-trip compatibility with to_dict() by recognizing
        nested "data" dictionaries from to_dict() output.

        Args:
            data: Dictionary of payload key-value pairs. May contain a nested
                "data" dict from to_dict() output for round-trip support.

        Returns:
            New ModelEnvelopePayload instance.

        Warns:
            UserWarning: When dict values are encountered and skipped (potential
                data loss). Nested dicts are not supported in CliValue | None.
        """
        known_fields = {"event_type", "source", "timestamp", "correlation_id", "data"}
        skipped_keys: list[str] = []

        # Extract typed fields
        event_type_val = data.get("event_type")
        source_val = data.get("source")
        timestamp_val = data.get("timestamp")
        correlation_id_val = data.get("correlation_id")

        # Handle nested "data" dict from to_dict() output for round-trip support
        nested_data = data.get("data")
        extra_data: dict[str, CliValue | None] = {}

        if isinstance(nested_data, dict):
            # to_dict() output format: {"data": {...}}
            for key, value in nested_data.items():
                # Ensure value is CliValue | None (not nested dict)
                # Note: isinstance check is defensive - type system says dict values
                # can't be dicts, but runtime may receive malformed input
                if isinstance(value, dict):
                    skipped_keys.append(f"data.{key}")  # type: ignore[unreachable]
                else:
                    extra_data[key] = value
        else:
            # Flat format: collect unknown fields into data dict
            for key, raw_value in data.items():
                if key not in known_fields:
                    if isinstance(raw_value, dict):
                        skipped_keys.append(key)
                    else:
                        # After isinstance check, raw_value is CliValue | None
                        # (dict type is excluded from the union)
                        extra_data[key] = raw_value

        # Warn about skipped dict values to prevent silent data loss
        if skipped_keys:
            warnings.warn(
                f"ModelEnvelopePayload.from_dict() skipped {len(skipped_keys)} dict "
                f"value(s) that cannot be represented in CliValue | None: "
                f"{skipped_keys}. Nested dicts are not supported.",
                UserWarning,
                stacklevel=2,
            )

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

        This method parses a flat string dictionary into a ModelEnvelopePayload.
        It recognizes typed fields (event_type, source, timestamp, correlation_id)
        and places remaining keys in the data dictionary.

        Warning:
            **NOT Round-Trip Compatible with to_string_dict()**

            This method and ``to_string_dict()`` are NOT guaranteed to be strict
            round-trip compatible. The following transformations are NOT reversible:

            1. **Reserved key prefixing**: ``to_string_dict()`` prefixes reserved
               keys (event_type, source, etc.) found in the data dict with "data_".
               ``from_string_dict()`` does NOT reverse this transformation, so
               "data_event_type" becomes a data key, not the original "event_type".

            2. **Boolean serialization**: ``to_string_dict()`` converts booleans
               to "true"/"false" strings. ``from_string_dict()`` does NOT convert
               them back to boolean type.

            3. **List serialization**: ``to_string_dict()`` joins lists with commas.
               ``from_string_dict()`` does NOT split them back into lists.

            4. **Type information loss**: All values become strings; original types
               (int, float, bool, list) are lost.

            For strict round-trip serialization, use ``to_dict()`` and ``from_dict()``
            with JSON serialization instead.

        Args:
            data: Dictionary of string key-value pairs.

        Returns:
            New ModelEnvelopePayload instance.

        Example:
            >>> # WARNING: Not round-trip compatible!
            >>> original = ModelEnvelopePayload(
            ...     event_type="test",
            ...     data={"count": 42, "enabled": True}
            ... )
            >>> string_dict = original.to_string_dict()
            >>> # string_dict = {"event_type": "test", "count": "42", "enabled": "true"}
            >>> restored = ModelEnvelopePayload.from_string_dict(string_dict)
            >>> # restored.data = {"count": "42", "enabled": "true"}  # strings, not int/bool!
        """
        # Convert to the wider type expected by from_dict
        converted: dict[str, CliValue | None | dict[str, CliValue | None]] = dict(data)
        return cls.from_dict(converted)

    def to_dict(self) -> dict[str, CliValue | None | dict[str, CliValue | None]]:
        """Convert to dictionary format.

        Returns:
            Dictionary representation with all fields.
        """
        result: dict[str, CliValue | None | dict[str, CliValue | None]] = {}
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
        """Convert to dict[str, str] format for HTTP transport.

        Flattens the structure to a simple string dictionary suitable for
        HTTP headers, query parameters, or other string-only contexts.
        Reserved keys in data dict are prefixed with "data_" to prevent
        collision with typed fields.

        Warning:
            **NOT Round-Trip Compatible with from_string_dict()**

            This method and ``from_string_dict()`` are NOT guaranteed to be strict
            round-trip compatible. Data transformations are ONE-WAY:

            1. **Reserved key prefixing**: Keys matching typed field names
               (event_type, source, timestamp, correlation_id, data) in the
               data dict are prefixed with "data_". This is NOT reversed by
               ``from_string_dict()``.

            2. **Boolean serialization**: ``True`` -> "true", ``False`` -> "false".
               NOT converted back to boolean by ``from_string_dict()``.

            3. **List serialization**: ``["a", "b"]`` -> "a,b".
               NOT split back into list by ``from_string_dict()``.

            4. **Numeric serialization**: ``42`` -> "42", ``3.14`` -> "3.14".
               NOT converted back to int/float by ``from_string_dict()``.

            For strict round-trip serialization, use ``to_dict()`` and ``from_dict()``
            with JSON serialization instead.

        Returns:
            Dictionary with string keys and values.

        Warns:
            UserWarning: When reserved keys in data dict are prefixed, or when
                the prefixed key would collide with an existing data key.

        Example:
            >>> payload = ModelEnvelopePayload(
            ...     event_type="test",
            ...     data={"count": 42, "tags": ["a", "b"]}
            ... )
            >>> payload.to_string_dict()
            {'event_type': 'test', 'count': '42', 'tags': 'a,b'}
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

        # Track collisions for warning
        prefixed_keys: list[str] = []
        collision_keys: list[str] = []

        # Flatten data items as string values
        # Reserved keys are prefixed with "data_" to prevent collision
        for key, value in self.data.items():
            if value is not None:
                # Prefix reserved keys to prevent collision with typed fields
                if key in self.RESERVED_KEYS:
                    output_key = f"data_{key}"
                    prefixed_keys.append(key)
                    # Check if prefixed key collides with another data key
                    if output_key in self.data:
                        collision_keys.append(output_key)
                else:
                    output_key = key

                if isinstance(value, bool):
                    result[output_key] = "true" if value else "false"
                elif isinstance(value, list):
                    result[output_key] = ",".join(value)
                else:
                    result[output_key] = str(value)

        # Warn about prefixed keys (potential data interpretation issues)
        if prefixed_keys:
            warnings.warn(
                f"ModelEnvelopePayload.to_string_dict() prefixed {len(prefixed_keys)} "
                f"reserved key(s) with 'data_': {prefixed_keys}. These keys collide "
                f"with typed field names and have been renamed.",
                UserWarning,
                stacklevel=2,
            )

        # Warn about collision with existing data keys (data loss risk)
        if collision_keys:
            warnings.warn(
                f"ModelEnvelopePayload.to_string_dict() detected key collision: "
                f"prefixed keys {collision_keys} already exist in data dict. "
                f"One value will overwrite the other, causing data loss.",
                UserWarning,
                stacklevel=2,
            )

        return result

    def get(self, key: str, default: CliValue | None = None) -> CliValue | None:
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

    def get_data(self, key: str, default: CliValue | None = None) -> CliValue | None:
        """Get a value from the data dictionary.

        Args:
            key: Data key to look up.
            default: Default value if key not found.

        Returns:
            Data value or default.
        """
        return self.data.get(key, default)

    def set_data(self, key: str, value: CliValue | None) -> Self:
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
        """Create a new instance with updated timestamp in ISO 8601 format.

        Converts the datetime to ISO 8601 string format for HTTP transport
        compatibility. If no timestamp is provided, uses UTC now.

        Args:
            timestamp: Timezone-aware datetime to set. Defaults to ``datetime.now(UTC)``.
                       Should be timezone-aware for consistent serialization.

        Returns:
            New ModelEnvelopePayload instance with timestamp as ISO 8601 string.

        Example:
            >>> payload = ModelEnvelopePayload(event_type="test")
            >>> updated = payload.with_timestamp()
            >>> updated.timestamp  # e.g., '2024-01-15T10:30:00+00:00'
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
        """Return True if there are any payload items.

        Warning:
            This differs from standard Pydantic behavior where ``bool(model)``
            always returns ``True``. An "empty" payload (all fields None/empty)
            returns ``False``, enabling idiomatic emptiness checks.

        Returns:
            bool: True if any payload field has data, False if all are empty.

        Example:
            >>> payload = ModelEnvelopePayload(event_type="test")
            >>> if payload:
            ...     print("Payload has content")
            Payload has content

            >>> empty = ModelEnvelopePayload()
            >>> if not empty:
            ...     print("Payload is empty")
            Payload is empty
        """
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


__all__ = ["ModelEnvelopePayload"]
