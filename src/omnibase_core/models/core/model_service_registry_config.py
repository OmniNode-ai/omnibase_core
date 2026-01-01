"""
Service registry configuration models.

Provides typed models for service configuration and discovery filters,
replacing dict[str, Any] patterns in registry action payloads.
"""

from pydantic import BaseModel, Field


class ModelServiceConfig(BaseModel):
    """
    Typed model for service configuration.

    Replaces dict[str, Any] service_config field in ModelRegistryActionPayload.
    """

    host: str | None = Field(
        default=None,
        description="Service host address",
    )
    port: int | None = Field(
        default=None,
        description="Service port number",
        ge=1,
        le=65535,
    )
    protocol: str | None = Field(
        default=None,
        description="Protocol (http, https, grpc, etc.)",
    )
    path_prefix: str | None = Field(
        default=None,
        description="URL path prefix for the service",
    )
    health_check_endpoint: str | None = Field(
        default=None,
        description="Health check endpoint path",
    )
    timeout_seconds: int | None = Field(
        default=None,
        description="Connection timeout in seconds",
        ge=1,
    )
    retry_count: int | None = Field(
        default=None,
        description="Number of retry attempts",
        ge=0,
    )
    weight: int | None = Field(
        default=None,
        description="Load balancing weight",
        ge=0,
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Service tags for categorization",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional string metadata",
    )


class ModelDiscoveryFilters(BaseModel):
    """
    Typed model for service discovery filters.

    Replaces dict[str, Any] discovery_filters field in ModelRegistryActionPayload.
    """

    service_type: str | None = Field(
        default=None,
        description="Filter by service type",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Filter by tags (any match)",
    )
    required_tags: list[str] = Field(
        default_factory=list,
        description="Filter by required tags (all must match)",
    )
    namespace: str | None = Field(
        default=None,
        description="Filter by namespace",
    )
    version_prefix: str | None = Field(  # string-version-ok: filter prefix pattern
        default=None,
        description="Filter by version prefix",
    )
    health_status: str | None = Field(
        default=None,
        description="Filter by health status (healthy, unhealthy, unknown)",
    )
    min_weight: int | None = Field(
        default=None,
        description="Minimum load balancing weight",
        ge=0,
    )
    max_results: int | None = Field(
        default=None,
        description="Maximum number of results",
        ge=1,
    )
    include_metadata: bool = Field(
        default=True,
        description="Include service metadata in results",
    )


__all__ = ["ModelServiceConfig", "ModelDiscoveryFilters"]
