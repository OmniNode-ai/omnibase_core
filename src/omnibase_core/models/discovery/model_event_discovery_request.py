"""Event Discovery Request model for ONEX Discovery & Integration Event Registry.

This module defines the request model for event discovery queries.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.discovery.model_event_descriptor import (
    EnumDiscoveryPhase,
    EnumEventType,
    EnumServiceStatus,
)


class ModelEventDiscoveryRequest(BaseModel):
    """Request model for event discovery queries."""

    query_id: UUID = Field(default=..., description="Unique query identifier")
    correlation_id: UUID = Field(
        default=..., description="Correlation ID for response matching"
    )

    # Discovery Filters
    service_name_pattern: str | None = Field(
        default=None,
        description="Service name pattern to match",
    )
    event_types: list[EnumEventType] = Field(
        default_factory=list,
        description="Event types to include",
    )
    discovery_phases: list[EnumDiscoveryPhase] = Field(
        default_factory=list,
        description="Discovery phases to include",
    )
    consul_tags: list[str] = Field(
        default_factory=list,
        description="Required Consul tags",
    )

    # Container Adapter Filters
    container_status_filter: list[EnumServiceStatus] = Field(
        default_factory=list,
        description="Container status filter",
    )
    hub_domain_filter: str | None = Field(default=None, description="Hub domain filter")
    trust_level_filter: list[str] = Field(
        default_factory=list,
        description="Trust level filter",
    )

    # Query Configuration
    max_results: int = Field(
        default=100, description="Maximum number of results to return"
    )
    include_inactive: bool = Field(
        default=False,
        description="Whether to include inactive services",
    )
    timeout_seconds: int = Field(default=30, description="Query timeout in seconds")

    model_config = ConfigDict(use_enum_values=True, extra="forbid")
