"""
Base model for runtime events.

Provides common fields for all ONEX runtime lifecycle events including
correlation tracking, timestamps, and event identification.
"""

from datetime import datetime
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
        default_factory=datetime.now,
        description="When this event was created",
    )
    source_node_id: UUID | None = Field(
        default=None,
        description="Node that generated this event",
    )
