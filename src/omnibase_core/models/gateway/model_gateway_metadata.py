"""
Strongly typed metadata models for gateway operations.

Replaces generic Dict[str, Union[...]] patterns with specific Pydantic models
for better type safety and clearer intent.
"""

from pydantic import BaseModel, Field


class GatewayMetadata(BaseModel):
    """
    Strongly typed metadata for gateway operations.

    Replaces: Dict[str, Union[str, int, float, bool]]
    """

    # Common gateway metadata fields
    node_type: str = Field(default="canary_gateway", description="Node type identifier")
    operation_type: str | None = Field(
        default=None,
        description="Type of gateway operation",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Request correlation ID",
    )

    # Performance metrics
    timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Operation timeout in milliseconds",
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Number of retries attempted",
    )
    priority_level: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Operation priority (1=highest, 10=lowest)",
    )

    # Routing configuration
    load_balance_weight: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Load balancing weight",
    )
    circuit_breaker_enabled: bool = Field(
        default=False,
        description="Whether circuit breaker is enabled",
    )
    health_check_enabled: bool = Field(
        default=True,
        description="Whether health checking is enabled",
    )

    # Service discovery
    service_registry: str | None = Field(
        default=None,
        description="Service registry used",
    )
    endpoint_version: str | None = Field(
        default=None,
        description="API version for endpoint",
    )

    # Debugging and monitoring
    trace_enabled: bool = Field(
        default=False,
        description="Whether distributed tracing is enabled",
    )
    debug_mode: bool = Field(default=False, description="Whether debug mode is enabled")

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
        validate_assignment = True
        extra = "forbid"  # Prevent unexpected fields


class LoadBalancingDecision(BaseModel):
    """
    Strongly typed load balancing decision metadata.

    Replaces: Dict[str, Union[str, int, float]]
    """

    algorithm: str = Field(description="Load balancing algorithm used")
    selected_endpoint: str = Field(description="Endpoint selected by algorithm")
    selection_reason: str = Field(description="Reason for endpoint selection")

    # Metrics that influenced decision
    endpoint_weight: float = Field(ge=0.0, description="Weight of selected endpoint")
    response_time_ms: float = Field(ge=0.0, description="Historical response time")
    active_connections: int = Field(ge=0, description="Current active connections")
    failure_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Recent failure rate (0.0-1.0)",
    )

    # Decision metadata
    alternatives_considered: int = Field(
        ge=1,
        description="Number of endpoints considered",
    )
    decision_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in decision (0.0-1.0)",
    )

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "forbid"


class ServiceDiscoveryMetadata(BaseModel):
    """
    Strongly typed service discovery metadata.

    Replaces: Dict[str, Union[str, int, float, bool]]
    """

    registry_type: str = Field(
        description="Type of service registry (consul, etcd, etc.)",
    )
    service_name: str = Field(description="Name of service being discovered")

    # Discovery configuration
    healthy_only: bool = Field(default=True, description="Only return healthy services")
    include_tags: list[str] = Field(
        default_factory=list,
        description="Tags to filter by",
    )
    max_instances: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum instances to return",
    )

    # Cache configuration
    cache_ttl_seconds: int = Field(
        default=30,
        ge=1,
        le=3600,
        description="Cache TTL in seconds",
    )
    cache_enabled: bool = Field(default=True, description="Whether caching is enabled")

    # Health checking
    health_check_timeout_ms: int = Field(
        default=5000,
        ge=100,
        le=30000,
        description="Health check timeout",
    )
    health_check_interval_ms: int = Field(
        default=10000,
        ge=1000,
        le=60000,
        description="Health check interval",
    )

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "forbid"


class DatabaseMetadata(BaseModel):
    """
    Strongly typed database connection metadata.

    Replaces: Dict[str, Union[str, int, float, bool, None]]
    """

    connection_type: str = Field(description="Type of database connection")
    database_name: str = Field(description="Name of database")

    # Connection configuration
    host: str = Field(description="Database host")
    port: int = Field(ge=1, le=65535, description="Database port")
    ssl_enabled: bool = Field(default=True, description="Whether SSL is enabled")

    # Pool configuration
    min_connections: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Minimum pool connections",
    )
    max_connections: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum pool connections",
    )
    connection_timeout_ms: int = Field(
        default=5000,
        ge=1000,
        le=30000,
        description="Connection timeout",
    )

    # Query configuration
    query_timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Query timeout",
    )
    auto_commit: bool = Field(
        default=True,
        description="Whether auto-commit is enabled",
    )

    # Monitoring
    slow_query_threshold_ms: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Slow query threshold",
    )
    enable_query_logging: bool = Field(
        default=False,
        description="Whether to log queries",
    )

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "forbid"
