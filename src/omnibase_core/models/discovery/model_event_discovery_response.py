"""Event Discovery Response model for ONEX Discovery & Integration Event Registry.

This module defines the response model for event discovery queries.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.discovery.model_event_descriptor import ModelEventDescriptor


class ModelEventDiscoveryResponse(BaseModel):
    """Response model for event discovery queries."""

    query_id: UUID = Field(default=..., description="Original query identifier")
    correlation_id: UUID = Field(default=..., description="Correlation ID from request")

    # Results
    discovered_events: list[ModelEventDescriptor] = Field(
        default_factory=list,
        description="Discovered events",
    )
    total_count: int = Field(default=0, description="Total number of matching events")
    result_count: int = Field(default=0, description="Number of events returned")

    # Response Metadata
    response_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Response timestamp",
    )
    consul_query_time_ms: int | None = Field(
        default=None,
        description="Consul query time in milliseconds",
    )
    container_adapter_active: bool = Field(
        default=True,
        description="Whether Container Adapter is active",
    )

    # Status Information
    query_successful: bool = Field(
        default=True, description="Whether query was successful"
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if query failed",
    )
    partial_results: bool = Field(
        default=False,
        description="Whether results are partial due to timeout",
    )

    model_config = ConfigDict(use_enum_values=True, extra="forbid")
