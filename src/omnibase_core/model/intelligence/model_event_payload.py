"""
Event payload model for intelligence system.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelEventPayload(BaseModel):
    """Event payload for intelligence events."""

    event_type: str = Field(..., description="Type of intelligence event")
    source_service: str = Field(..., description="Service that generated the event")
    payload_data: str = Field(..., description="Event payload as JSON string")
    correlation_id: Optional[str] = Field(
        None, description="Correlation ID for tracing"
    )
    timestamp: str = Field(..., description="Event timestamp")
