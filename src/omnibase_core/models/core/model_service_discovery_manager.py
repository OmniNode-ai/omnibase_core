"""
ONEX Service Discovery Manager Model

Pydantic model for service discovery and resolution configuration.
Follows ONEX conventions: CamelCase model name, one model per file.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelServiceDiscoveryManager(BaseModel):
    """
    ONEX-compatible model for service discovery manager configuration.

    Represents the configuration for service discovery with Consul integration,
    static configuration fallback, and service caching capabilities.
    """

    consul_enabled: bool = Field(
        default=True,
        description="Whether Consul service discovery is enabled",
    )

    consul_datacenter: str = Field(
        default="dc1",
        description="Consul datacenter for service discovery",
    )

    consul_timeout: int = Field(
        default=10,
        description="Consul connection timeout in seconds",
    )

    static_config: SerializedDict = Field(
        default_factory=dict,
        description="Static service configuration mappings",
    )

    service_cache_enabled: bool = Field(
        default=True,
        description="Whether to cache resolved services",
    )

    cache_ttl: int = Field(default=300, description="Service cache TTL in seconds")

    fallback_strategies: list[str] = Field(
        default_factory=lambda: ["consul", "static", "fallback"],
        description="Ordered list of service resolution strategies",
    )

    supported_protocols: list[str] = Field(
        default_factory=list,
        description="List of supported protocol types for resolution",
    )

    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for failed service discovery",
    )

    health_check_interval: int = Field(
        default=30,
        description="Service health check interval in seconds",
    )
