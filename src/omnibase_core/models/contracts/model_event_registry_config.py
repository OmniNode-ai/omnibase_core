"""
Event Registry Configuration Model.

Defines service discovery, automatic provisioning,
and registry integration for event management.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEventRegistryConfig(BaseModel):
    """
    Event Registry integration configuration.

    Defines service discovery, automatic provisioning,
    and registry integration for event management.
    """

    discovery_enabled: bool = Field(
        default=True,
        description="Enable automatic event discovery",
    )

    auto_provisioning_enabled: bool = Field(
        default=True,
        description="Enable automatic event provisioning",
    )

    registry_endpoint: str | None = Field(
        default=None,
        description="Event Registry service endpoint",
    )

    health_check_enabled: bool = Field(
        default=True,
        description="Enable Event Registry health checking",
    )

    health_check_interval_s: int = Field(
        default=30,
        description="Health check interval in seconds",
        ge=1,
    )

    cache_enabled: bool = Field(
        default=True,
        description="Enable registry data caching",
    )

    cache_ttl_s: int = Field(
        default=300,
        description="Registry cache TTL in seconds",
        ge=1,
    )

    security_enabled: bool = Field(
        default=True,
        description="Enable security for registry communication",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
