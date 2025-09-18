"""
Node-specific configuration models for contract content.

Provides strongly typed configuration models for different node types.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelAggregationConfig(BaseModel):
    """Aggregation configuration for nodes."""

    model_config = ConfigDict(extra="forbid")

    strategy: str = Field(
        ...,
        description="Aggregation strategy (sum, average, max, min, etc.)",
    )
    window_size: int | None = Field(
        None,
        description="Aggregation window size",
        ge=1,
    )
    batch_size: int | None = Field(
        None,
        description="Batch size for aggregation",
        ge=1,
    )
    timeout_ms: int | None = Field(
        None,
        description="Aggregation timeout in milliseconds",
        ge=0,
    )


class ModelStateManagementConfig(BaseModel):
    """State management configuration."""

    model_config = ConfigDict(extra="forbid")

    persistence: bool = Field(
        default=False,
        description="Whether state should be persisted",
    )
    storage_type: str | None = Field(
        None,
        description="Storage type for state (memory, disk, database)",
    )
    compression: bool = Field(
        default=False,
        description="Whether to compress stored state",
    )
    expiry_seconds: int | None = Field(
        None,
        description="State expiry time in seconds",
        ge=0,
    )


class ModelStreamingConfig(BaseModel):
    """Streaming configuration for REDUCER nodes."""

    model_config = ConfigDict(extra="forbid")

    buffer_size: int = Field(
        default=1000,
        description="Stream buffer size",
        ge=1,
    )
    batch_timeout_ms: int = Field(
        default=1000,
        description="Batch timeout in milliseconds",
        ge=1,
    )
    backpressure_strategy: str = Field(
        default="buffer",
        description="Backpressure handling strategy",
    )
    parallel_streams: int = Field(
        default=1,
        description="Number of parallel streams",
        ge=1,
    )


class ModelConflictResolutionConfig(BaseModel):
    """Conflict resolution configuration for REDUCER nodes."""

    model_config = ConfigDict(extra="forbid")

    strategy: str = Field(
        ...,
        description="Conflict resolution strategy (last_write_wins, merge, etc.)",
    )
    merge_fields: list[str] | None = Field(
        None,
        description="Fields to merge in case of conflicts",
    )
    priority_field: str | None = Field(
        None,
        description="Field to use for priority-based resolution",
    )


class ModelMemoryManagementConfig(BaseModel):
    """Memory management configuration for REDUCER nodes."""

    model_config = ConfigDict(extra="forbid")

    max_memory_mb: int = Field(
        default=512,
        description="Maximum memory usage in megabytes",
        ge=1,
    )
    gc_threshold: float = Field(
        default=0.8,
        description="Garbage collection threshold (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    cleanup_strategy: str = Field(
        default="lru",
        description="Memory cleanup strategy (lru, fifo, random)",
    )


class ModelRoutingConfig(BaseModel):
    """Routing configuration for ORCHESTRATOR nodes."""

    model_config = ConfigDict(extra="forbid")

    strategy: str = Field(
        ...,
        description="Routing strategy (round_robin, hash, weighted, etc.)",
    )
    load_balancing: bool = Field(
        default=True,
        description="Enable load balancing",
    )
    health_check_interval_ms: int = Field(
        default=30000,
        description="Health check interval in milliseconds",
        ge=1000,
    )
    failover_enabled: bool = Field(
        default=True,
        description="Enable automatic failover",
    )


class ModelWorkflowRegistryConfig(BaseModel):
    """Workflow registry configuration for ORCHESTRATOR nodes."""

    model_config = ConfigDict(extra="forbid")

    storage_type: str = Field(
        default="memory",
        description="Storage type for workflow registry",
    )
    max_workflows: int = Field(
        default=10000,
        description="Maximum number of workflows to store",
        ge=1,
    )
    cleanup_interval_ms: int = Field(
        default=300000,
        description="Cleanup interval in milliseconds",
        ge=60000,
    )


class ModelInterfaceConfig(BaseModel):
    """Interface configuration for EFFECT nodes."""

    model_config = ConfigDict(extra="forbid")

    protocol: str = Field(
        ...,
        description="Interface protocol (http, grpc, websocket, etc.)",
    )
    host: str | None = Field(
        None,
        description="Interface host",
    )
    port: int | None = Field(
        None,
        description="Interface port",
        ge=1,
        le=65535,
    )
    ssl_enabled: bool = Field(
        default=False,
        description="Whether SSL is enabled",
    )
    authentication: str | None = Field(
        None,
        description="Authentication method",
    )


class ModelCachingConfig(BaseModel):
    """Caching configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Whether caching is enabled",
    )
    ttl_seconds: int = Field(
        default=300,
        description="Cache TTL in seconds",
        ge=0,
    )
    max_size: int = Field(
        default=1000,
        description="Maximum cache size",
        ge=1,
    )
    eviction_policy: str = Field(
        default="lru",
        description="Cache eviction policy",
    )


class ModelErrorHandlingConfig(BaseModel):
    """Error handling configuration."""

    model_config = ConfigDict(extra="forbid")

    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts",
        ge=0,
    )
    backoff_strategy: str = Field(
        default="exponential",
        description="Backoff strategy for retries",
    )
    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable circuit breaker pattern",
    )
    error_threshold: int = Field(
        default=5,
        description="Error threshold for circuit breaker",
        ge=1,
    )


class ModelObservabilityConfig(BaseModel):
    """Observability configuration."""

    model_config = ConfigDict(extra="forbid")

    metrics_enabled: bool = Field(
        default=True,
        description="Enable metrics collection",
    )
    tracing_enabled: bool = Field(
        default=True,
        description="Enable distributed tracing",
    )
    logging_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    health_check_endpoint: bool = Field(
        default=True,
        description="Enable health check endpoint",
    )


class ModelEventTypeConfig(BaseModel):
    """Event type configuration for publish/subscribe patterns."""

    model_config = ConfigDict(extra="forbid")

    event_name: str = Field(
        ...,
        description="Event type name",
    )
    schema: str | None = Field(
        None,
        description="Event schema specification",
    )
    routing_key: str | None = Field(
        None,
        description="Routing key for the event",
    )
    persistence: bool = Field(
        default=False,
        description="Whether events should be persisted",
    )
