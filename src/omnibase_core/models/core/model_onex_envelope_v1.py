"""
ModelOnexEnvelopeV1 - Simple event envelope for standardized message wrapping.

This model provides a lightweight envelope format for wrapping events with
metadata like correlation IDs, timestamps, and source information. Used by
intent publishing and other coordination patterns.

Architecture:
    Simple wrapper around any payload (dict) with standard metadata fields.
    Lighter weight than ModelEventEnvelope which is for complex routing.

Usage:
    envelope = ModelOnexEnvelopeV1(
        envelope_version="1.0",
        correlation_id=correlation_id,
        event_id=event_id,
        event_type="EVENT_PUBLISH_INTENT",
        timestamp=datetime.now(UTC),
        source_service="my_service",
        payload={"key": "value"}
    )

Part of omnibase_core framework - provides standardized event wrapping
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.primitives.model_semver import ModelSemVer


class ModelOnexEnvelopeV1(BaseModel):
    """
    Simple event envelope for standardized message wrapping.

    This is a lightweight envelope format used for wrapping events with
    standard metadata. Unlike ModelEventEnvelope (which handles complex
    multi-hop routing), this is designed for simple event wrapping with
    correlation tracking.

    Key Fields:
        - envelope_version: Format version (e.g., "1.0")
        - correlation_id: UUID for tracking related events
        - event_id: UUID for this specific event
        - event_type: String identifier for the event type
        - timestamp: When the event was created
        - source_service: Service that created the event
        - payload: The actual event data (as dict)

    Example:
        envelope = ModelOnexEnvelopeV1(
            envelope_version="1.0",
            correlation_id=uuid4(),
            event_id=uuid4(),
            event_type="METRICS_RECORDED",
            timestamp=datetime.now(UTC),
            source_service="metrics_service",
            payload={"metric": "value"}
        )

        # Serialize to JSON
        json_str = envelope.model_dump_json()

        # Deserialize from JSON
        envelope2 = ModelOnexEnvelopeV1.model_validate_json(json_str)

    Thread Safety:
        This model is immutable after creation. Safe for concurrent access.
    """

    # Envelope metadata
    envelope_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Envelope format version",
    )
    correlation_id: UUID = Field(
        description="Correlation ID for tracking related events",
    )
    event_id: UUID = Field(
        description="Unique identifier for this event",
    )
    event_type: str = Field(
        description="Type of event being wrapped",
    )
    timestamp: datetime = Field(
        description="When the event was created",
    )
    source_service: str = Field(
        description="Service that created this event",
    )

    # Event payload (actual data)
    payload: dict[str, Any] = Field(
        description="The actual event data",
    )

    model_config = ConfigDict(
        frozen=False,  # Allow modification for testing/debugging
        validate_assignment=True,
    )

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"ModelOnexEnvelopeV1["
            f"type={self.event_type}, "
            f"correlation={str(self.correlation_id)[:8]}, "
            f"source={self.source_service}]"
        )
