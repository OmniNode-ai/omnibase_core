"""Pending request tracking model for event-driven discovery."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.constants import KAFKA_REQUEST_TIMEOUT_MS
from omnibase_core.models.discovery.model_introspection_filters import (
    ModelIntrospectionFilters,
)


class ModelPendingRequest(BaseModel):
    """Tracks pending introspection requests for correlation."""

    correlation_id: UUID = Field(
        default=...,
        description="Unique correlation ID for request-response matching",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When request was initiated",
    )
    request_type: str = Field(
        default="tool_discovery",
        description="Type of discovery request",
    )
    filters: ModelIntrospectionFilters | None = Field(
        default=None,
        description="Filters applied to the discovery request",
    )
    timeout_ms: int = Field(
        default=KAFKA_REQUEST_TIMEOUT_MS, description="Request timeout in milliseconds"
    )

    def is_expired(self) -> bool:
        """Check if request has expired based on timeout."""
        age_ms = (datetime.now() - self.timestamp).total_seconds() * 1000
        return age_ms > self.timeout_ms
