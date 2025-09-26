"""
Strongly-typed event metadata structure.

Replaces dict[str, Any] usage in event metadata with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any


class ModelEventMetadata(BaseModel):
    """
    Strongly-typed event metadata.

    Replaces dict[str, Any] with structured event metadata model.
    """

    event_id: UUID = Field(
        default_factory=uuid4, description="Unique event identifier (UUID format)"
    )
    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Event timestamp"
    )
    source: str = Field(..., description="Event source identifier")

    # Event processing
    processed: bool = Field(default=False, description="Whether event was processed")
    processing_duration_ms: int = Field(default=0, description="Processing duration")
    retry_count: int = Field(default=0, description="Number of retry attempts")

    # Event routing
    target_handlers: dict[str, str] = Field(
        default_factory=dict, description="Target event handlers"
    )
    routing_key: str = Field(default="", description="Event routing key")

    # Context information
    user_id: UUID | None = Field(
        default=None, description="User identifier (UUID format)"
    )
    session_id: UUID | None = Field(
        default=None, description="Session identifier (UUID format)"
    )
    request_id: UUID | None = Field(
        default=None, description="Request identifier (UUID format)"
    )


# Export for use
__all__ = ["ModelEventMetadata"]
