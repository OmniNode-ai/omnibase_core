"""Model for service discovery and registration test data."""

from pydantic import BaseModel, Field


class ModelServiceRegistrationData(BaseModel):
    """Strongly-typed model for service registration data."""

    service_id: str = Field(description="Unique service identifier")
    service_name: str = Field(description="Human-readable service name")
    service_address: str = Field(description="Service network address")
    service_port: int = Field(description="Service port number")
    service_tags: list[str] = Field(
        default_factory=list,
        description="Service tags for categorization",
    )
    health_check_url: str | None = Field(
        default=None,
        description="URL for health check endpoint",
    )
    metadata: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Additional service metadata",
    )


class ModelServiceDiscoveryResult(BaseModel):
    """Strongly-typed model for service discovery results."""

    services: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Map of service names to their tags",
    )
    service_details: list[ModelServiceRegistrationData] = Field(
        default_factory=list,
        description="Detailed service information",
    )
    discovery_timestamp: float = Field(
        description="Timestamp when discovery was performed",
    )
    consul_health: bool = Field(
        default=True,
        description="Whether Consul was healthy during discovery",
    )
