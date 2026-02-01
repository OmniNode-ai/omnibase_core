"""
Idempotency Configuration Model for Projector Contracts.

Provides configuration for idempotent event processing in projectors.
Idempotency ensures that processing the same event multiple times
produces the same result, enabling safe retries and replay.

The key field specifies which event attribute to use for deduplication.
Common choices include:
    - ``sequence_number``: Event sequence in a stream
    - ``event_id``: Unique event identifier
    - ``correlation_id``: Request correlation identifier

Example Usage:
    >>> from omnibase_core.models.projectors import ModelIdempotencyConfig
    >>>
    >>> # Enable idempotency with sequence_number as key
    >>> config = ModelIdempotencyConfig(key="sequence_number")
    >>> config.enabled
    True
    >>>
    >>> # Disable idempotency (e.g., for stateless projectors)
    >>> config = ModelIdempotencyConfig(enabled=False, key="event_id")
    >>> config.enabled
    False

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access.

.. versionadded:: 0.4.0
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelIdempotencyConfig(BaseModel):
    """
    Idempotency configuration for projector event processing.

    Idempotency ensures that processing the same event multiple times
    produces the same result. This is critical for:
        - Safe retries after failures
        - Event replay during recovery
        - Exactly-once processing semantics

    Attributes:
        enabled: Whether idempotency checking is enabled. When True,
            the projector tracks processed event keys and skips
            duplicates. Defaults to True.
        key: The event attribute to use as the idempotency key.
            This field uniquely identifies an event for deduplication.
            Common values: "sequence_number", "event_id", "correlation_id".

    Examples:
        Basic configuration with sequence number:

        >>> config = ModelIdempotencyConfig(key="sequence_number")
        >>> config.enabled
        True
        >>> config.key
        'sequence_number'

        Disabled idempotency:

        >>> config = ModelIdempotencyConfig(enabled=False, key="event_id")
        >>> config.enabled
        False

    Note:
        **Why from_attributes=True is Required**

        This model uses ``from_attributes=True`` in its ConfigDict to ensure
        pytest-xdist compatibility. When running tests with pytest-xdist,
        each worker process imports the class independently, creating separate
        class objects. The ``from_attributes=True`` flag enables Pydantic's
        "duck typing" mode, allowing fixtures from one worker to be validated
        in another.

        **Thread Safety**: This model is frozen (immutable) after creation,
        making it thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    enabled: bool = Field(
        default=True,
        description="Whether idempotency checking is enabled",
    )

    key: str = Field(
        ...,
        description="Event attribute to use as the idempotency key (e.g., 'sequence_number', 'event_id')",
    )

    def __repr__(self) -> str:
        """Return a concise representation for debugging.

        Returns:
            String representation showing enabled status and key.

        Examples:
            >>> config = ModelIdempotencyConfig(key="sequence_number")
            >>> repr(config)
            "ModelIdempotencyConfig(enabled=True, key='sequence_number')"
        """
        return f"ModelIdempotencyConfig(enabled={self.enabled}, key={self.key!r})"


__all__ = ["ModelIdempotencyConfig"]
