"""
Consul service discovery models.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.node import EnumHealthStatus


class ModelServiceInstance(BaseModel):
    """Represents a discovered service instance."""

    service_id: str = Field(
        ...,
        description="Unique identifier for this service instance",
    )
    service_name: str = Field(..., description="Name of the service")
    address: str = Field(..., description="IP address or hostname of the service")
    port: int = Field(..., description="Port on which the service is listening")
    health_status: EnumHealthStatus = Field(
        ...,
        description="Current health status of the service",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags associated with the service",
    )
    meta: dict[str, str] = Field(
        default_factory=dict,
        description="Metadata key-value pairs",
    )
    datacenter: str = Field(
        ...,
        description="Consul datacenter where service is registered",
    )


class ModelServiceDiscoveryRequest(BaseModel):
    """Request for service discovery operations."""

    service_name: str = Field(..., description="Name of the service to discover")
    datacenter: str | None = Field(
        None,
        description="Specific datacenter to search (default: local)",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Required tags for filtering services",
    )
    healthy_only: bool = Field(
        True,
        description="Only return healthy service instances",
    )


class ModelServiceDiscoveryResult(BaseModel):
    """Result of service discovery operation."""

    success: bool = Field(..., description="Whether the discovery was successful")
    services: list[ModelServiceInstance] = Field(
        default_factory=list,
        description="List of discovered service instances",
    )
    query_time_ms: float = Field(
        ...,
        description="Time taken for the discovery query in milliseconds",
    )
    consul_agent_url: str = Field(
        ...,
        description="URL of the Consul agent used for discovery",
    )
    error_message: str | None = Field(
        None,
        description="Error message if discovery failed",
    )
