#!/usr/bin/env python3
"""
Routing Subcontract Model - ONEX Microservices Architecture Compliant.

Advanced subcontract model for ONEX microservices routing functionality providing:
- Route definitions with conditions and service targets
- Load balancing and failover strategies for microservices
- Circuit breaker and health check configuration
- Request/response transformation rules with correlation tracking
- Routing metrics and distributed tracing for microservices observability
- Service mesh integration patterns
- Container-aware routing for ONEX 4-node architecture

This model is composed into node contracts that require routing functionality,
providing clean separation between node logic and routing behavior optimized
for ONEX microservices ecosystem.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ModelRouteDefinition(BaseModel):
    """
    Route definition for ONEX microservices routing.

    Defines routing rules, conditions, service targets,
    and transformation logic for request forwarding in ONEX ecosystem.
    """

    route_id: UUID = Field(default_factory=uuid4, description="Unique route identifier")

    route_name: str = Field(..., description="Unique name for the route", min_length=1)

    route_pattern: str = Field(
        ...,
        description="Pattern for matching requests (supports service discovery patterns)",
        min_length=1,
    )

    method: str | None = Field(
        default=None,
        description="HTTP method filter (GET, POST, etc.)",
    )

    conditions: list[str] = Field(
        default_factory=list,
        description="Conditions for route matching (supports service mesh conditions)",
    )

    service_targets: list[str] = Field(
        ...,
        description="Target microservice endpoints for routing",
        min_length=1,
    )

    weight: int = Field(
        default=100,
        description="Route weight for load balancing",
        ge=0,
        le=1000,
    )

    priority: int = Field(
        default=1,
        description="Route priority for conflict resolution",
        ge=1,
    )

    timeout_ms: int = Field(
        default=30000,
        description="Timeout for route requests",
        ge=100,
    )

    retry_enabled: bool = Field(
        default=True,
        description="Enable retry for failed requests",
    )

    max_retries: int = Field(default=3, description="Maximum number of retries", ge=0)

    # ONEX microservices specific features
    service_mesh_enabled: bool = Field(
        default=True,
        description="Enable service mesh integration",
    )

    correlation_id_required: bool = Field(
        default=True,
        description="Require correlation ID for request tracking",
    )


class ModelLoadBalancing(BaseModel):
    """
    Load balancing configuration for ONEX microservices.

    Defines load balancing strategies optimized for microservices,
    health checking, and failover policies with service discovery integration.
    """

    strategy: str = Field(
        default="service_aware_round_robin",
        description="Load balancing strategy (service_aware_round_robin, consistent_hash, least_connections, weighted_response_time)",
    )

    health_check_enabled: bool = Field(
        default=True,
        description="Enable health checking for targets",
    )

    health_check_path: str = Field(
        default="/health",
        description="Health check endpoint path",
    )

    health_check_interval_ms: int = Field(
        default=30000,
        description="Health check interval",
        ge=1000,
    )

    health_check_timeout_ms: int = Field(
        default=5000,
        description="Health check timeout",
        ge=100,
    )

    unhealthy_threshold: int = Field(
        default=3,
        description="Failures before marking unhealthy",
        ge=1,
    )

    healthy_threshold: int = Field(
        default=2,
        description="Successes before marking healthy",
        ge=1,
    )

    sticky_sessions: bool = Field(
        default=False,
        description="Enable sticky session routing",
    )

    session_affinity_cookie: str | None = Field(
        default=None,
        description="Cookie name for session affinity",
    )

    # ONEX microservices specific load balancing features
    service_discovery_enabled: bool = Field(
        default=True,
        description="Enable automatic service discovery for targets",
    )

    container_aware_routing: bool = Field(
        default=True,
        description="Enable container-aware routing for ONEX 4-node architecture",
    )

    node_type_affinity: str | None = Field(
        default=None,
        description="Preferred ONEX node type (Effect, Compute, Reducer, Orchestrator)",
    )


class ModelCircuitBreaker(BaseModel):
    """
    Circuit breaker configuration.

    Defines circuit breaker behavior for fault tolerance,
    including failure thresholds and recovery policies.
    """

    enabled: bool = Field(
        default=True,
        description="Enable circuit breaker functionality",
    )

    failure_threshold: int = Field(
        default=5,
        description="Failures before opening circuit",
        ge=1,
    )

    success_threshold: int = Field(
        default=3,
        description="Successes before closing circuit",
        ge=1,
    )

    timeout_ms: int = Field(default=60000, description="Circuit open timeout", ge=1000)

    half_open_max_calls: int = Field(
        default=3,
        description="Max calls in half-open state",
        ge=1,
    )

    failure_rate_threshold: float = Field(
        default=0.5,
        description="Failure rate threshold",
        ge=0.0,
        le=1.0,
    )

    minimum_calls: int = Field(
        default=10,
        description="Minimum calls before evaluation",
        ge=1,
    )

    slow_call_duration_ms: int = Field(
        default=60000,
        description="Duration for slow call detection",
        ge=1000,
    )

    slow_call_rate_threshold: float = Field(
        default=0.6,
        description="Slow call rate threshold",
        ge=0.0,
        le=1.0,
    )


class ModelRequestTransformation(BaseModel):
    """
    Request transformation configuration.

    Defines request/response transformation rules,
    header manipulation, and payload modification.
    """

    transformation_enabled: bool = Field(
        default=False,
        description="Enable request transformation",
    )

    header_transformations: dict[str, str] = Field(
        default_factory=dict,
        description="Header transformation rules",
    )

    path_rewrite_rules: list[str] = Field(
        default_factory=list,
        description="Path rewrite patterns",
    )

    query_parameter_rules: dict[str, str] = Field(
        default_factory=dict,
        description="Query parameter transformation",
    )

    payload_transformation: str | None = Field(
        default=None,
        description="Payload transformation template",
    )

    response_transformation: bool = Field(
        default=False,
        description="Enable response transformation",
    )

    response_header_rules: dict[str, str] = Field(
        default_factory=dict,
        description="Response header transformation",
    )


class ModelRoutingMetrics(BaseModel):
    """
    Routing metrics configuration.

    Defines metrics collection, monitoring,
    and alerting for routing operations.
    """

    metrics_enabled: bool = Field(
        default=True,
        description="Enable routing metrics collection",
    )

    detailed_metrics: bool = Field(
        default=False,
        description="Enable detailed per-route metrics",
    )

    latency_buckets: list[float] = Field(
        default_factory=lambda: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
        description="Latency histogram buckets",
    )

    error_rate_threshold: float = Field(
        default=0.05,
        description="Error rate alerting threshold",
        ge=0.0,
        le=1.0,
    )

    latency_threshold_ms: int = Field(
        default=5000,
        description="Latency alerting threshold",
        ge=100,
    )

    sampling_rate: float = Field(
        default=1.0,
        description="Metrics sampling rate",
        ge=0.0,
        le=1.0,
    )


class ModelRoutingSubcontract(BaseModel):
    """
    ONEX Microservices Routing subcontract model for request routing functionality.

    Comprehensive routing subcontract providing route definitions,
    load balancing, circuit breaking, and request transformation optimized
    for ONEX microservices ecosystem. Designed for composition into node
    contracts requiring routing functionality with service mesh integration.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Core routing configuration
    routing_id: UUID = Field(
        default_factory=uuid4,
        description="Unique routing configuration identifier",
    )

    routing_enabled: bool = Field(
        default=True,
        description="Enable routing functionality",
    )

    routing_strategy: str = Field(
        default="service_mesh_aware",
        description="Primary routing strategy (service_mesh_aware, path_based, header_based, container_aware)",
    )

    default_target: str | None = Field(
        default=None,
        description="Default target for unmatched requests",
    )

    # Route definitions
    routes: list[ModelRouteDefinition] = Field(
        default_factory=list,
        description="Route definitions",
    )

    # Load balancing configuration
    load_balancing: ModelLoadBalancing = Field(
        default_factory=ModelLoadBalancing,
        description="Load balancing configuration",
    )

    # Circuit breaker configuration
    circuit_breaker: ModelCircuitBreaker = Field(
        default_factory=ModelCircuitBreaker,
        description="Circuit breaker configuration",
    )

    # Request/Response transformation
    transformation: ModelRequestTransformation = Field(
        default_factory=ModelRequestTransformation,
        description="Request transformation configuration",
    )

    # Routing metrics and monitoring
    metrics: ModelRoutingMetrics = Field(
        default_factory=ModelRoutingMetrics,
        description="Routing metrics configuration",
    )

    # Advanced routing features
    rate_limiting_enabled: bool = Field(
        default=False,
        description="Enable rate limiting per route",
    )

    rate_limit_requests_per_minute: int = Field(
        default=1000,
        description="Rate limit threshold",
        ge=1,
    )

    cors_enabled: bool = Field(default=False, description="Enable CORS handling")

    cors_origins: list[str] = Field(
        default_factory=list,
        description="Allowed CORS origins",
    )

    # Security and authentication
    authentication_required: bool = Field(
        default=False,
        description="Require authentication for routes",
    )

    authorization_rules: list[str] = Field(
        default_factory=list,
        description="Authorization rules for routes",
    )

    # Request logging and tracing
    request_logging: bool = Field(default=True, description="Enable request logging")

    trace_sampling_rate: float = Field(
        default=0.1,
        description="Distributed tracing sampling rate",
        ge=0.0,
        le=1.0,
    )

    # Connection and timeout management
    connection_pool_size: int = Field(
        default=100,
        description="Connection pool size per target",
        ge=1,
    )

    keep_alive_timeout_ms: int = Field(
        default=60000,
        description="Keep-alive timeout",
        ge=1000,
    )

    idle_timeout_ms: int = Field(
        default=300000,
        description="Idle connection timeout",
        ge=1000,
    )

    # Failover and disaster recovery
    failover_enabled: bool = Field(
        default=True,
        description="Enable automatic failover",
    )

    backup_targets: list[str] = Field(
        default_factory=list,
        description="Backup targets for failover",
    )

    disaster_recovery_mode: bool = Field(
        default=False,
        description="Enable disaster recovery mode",
    )

    # ONEX Microservices Ecosystem Integration
    onex_node_type_routing: bool = Field(
        default=True,
        description="Enable ONEX 4-node architecture aware routing",
    )

    service_mesh_integration: bool = Field(
        default=True,
        description="Enable service mesh integration for ONEX ecosystem",
    )

    correlation_tracking: bool = Field(
        default=True,
        description="Enable correlation ID tracking across service calls",
    )

    container_orchestration_aware: bool = Field(
        default=True,
        description="Enable container orchestration awareness (Docker, Kubernetes)",
    )

    # Service discovery and registry integration
    consul_integration: bool = Field(
        default=True,
        description="Enable Consul service discovery integration",
    )

    redis_routing_cache: bool = Field(
        default=True,
        description="Enable Redis-based routing cache for performance",
    )

    # Advanced ONEX patterns
    event_driven_routing: bool = Field(
        default=False,
        description="Enable event-driven routing patterns via RedPanda/event bus",
    )

    workflow_aware_routing: bool = Field(
        default=False,
        description="Enable workflow-aware routing for multi-step processes",
    )

    @field_validator("routes")
    @classmethod
    def validate_route_priorities_unique(
        cls,
        v: list[ModelRouteDefinition],
    ) -> list[ModelRouteDefinition]:
        """Validate that route priorities are unique within same pattern."""
        pattern_priorities: dict[tuple[str, str], int] = {}
        for route in v:
            key = (route.route_pattern, route.method or "*")
            if key in pattern_priorities and pattern_priorities[key] == route.priority:
                msg = f"Duplicate priority {route.priority} for pattern {route.route_pattern}"
                raise ValueError(
                    msg,
                )
            pattern_priorities[key] = route.priority
        return v

    @field_validator("trace_sampling_rate")
    @classmethod
    def validate_sampling_rate(cls, v: float) -> float:
        """Validate sampling rate is reasonable."""
        if v > 0.5:
            msg = "Trace sampling rate above 50% may impact performance"
            raise ValueError(msg)
        return v

    model_config = {
        "extra": "ignore",  # Allow extra fields from YAML contracts
        "use_enum_values": False,  # Keep enum objects, don't convert to strings
        "validate_assignment": True,
    }
