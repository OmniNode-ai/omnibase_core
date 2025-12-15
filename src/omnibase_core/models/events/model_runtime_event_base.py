"""
Base model for runtime events.

Provides common fields for all ONEX runtime lifecycle events including
correlation tracking, timestamps, and event identification.

Timezone Handling:
    All datetime fields in runtime event models use timezone-aware UTC timestamps
    via ``datetime.now(UTC)`` from Python 3.11+. This ensures:

    1. Consistent timezone handling across distributed systems
    2. Proper serialization/deserialization of timestamps
    3. Accurate time comparisons and elapsed time calculations

    When subclassing, always use ``datetime.now(UTC)`` for datetime default factories:

        field_at: datetime = Field(
            default_factory=lambda: datetime.now(UTC),
            description="When something occurred (UTC)",
        )

    Note: ``ModelEnvelopePayload.timestamp`` uses ``str`` type instead of ``datetime``
    because that model is designed for serialization to string dictionaries (HTTP headers,
    query params). Use ``ModelEnvelopePayload.with_timestamp()`` to set UTC timestamps.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelRuntimeEventBase"]


class ModelRuntimeEventBase(BaseModel):
    """
    Base model for all runtime events.

    Provides common fields for correlation tracking, timestamps,
    and event identification.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        from_attributes=True,
    )

    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this event instance",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for request tracing across services",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this event was created (UTC)",
    )
    source_node_id: UUID | None = Field(
        default=None,
        description="Node that generated this event",
    )
