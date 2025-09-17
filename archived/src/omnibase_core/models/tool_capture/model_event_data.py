"""
Event statistics model for Tool Capture Events Service.

Represents statistics for event processing and storage.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelEventStatistics(BaseModel):
    """Statistics for event processing and storage."""

    total_events_sent: int = Field(..., description="Total events sent to event bus")
    total_events_failed: int = Field(
        ...,
        description="Total events that failed to send",
    )
    events_by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Count of events by type",
    )
    last_event_timestamp: datetime | None = Field(
        None,
        description="Timestamp of last event",
    )
    event_bus_connection_active: bool = Field(
        False,
        description="Whether event bus connection is active",
    )
    average_send_time_ms: float = Field(
        0.0,
        description="Average time to send events in milliseconds",
    )
