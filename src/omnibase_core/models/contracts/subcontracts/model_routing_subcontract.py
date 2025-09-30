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

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

from .model_circuit_breaker import ModelCircuitBreaker
from .model_load_balancing import ModelLoadBalancing
from .model_request_transformation import ModelRequestTransformation
from .model_route_definition import ModelRouteDefinition
from .model_routing_metrics import ModelRoutingMetrics


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
        # Group routes by pattern to check priority uniqueness within each pattern
        pattern_routes: dict[str, list[ModelRouteDefinition]] = {}

        for route in v:
            pattern = route.route_pattern
            if pattern not in pattern_routes:
                pattern_routes[pattern] = []
            pattern_routes[pattern].append(route)

        # Check for duplicate priorities within each pattern group
        for pattern, routes in pattern_routes.items():
            priorities_seen = set()
            for route in routes:
                if route.priority in priorities_seen:
                    msg = f"Duplicate priority {route.priority} found in pattern '{pattern}' (route: {route.route_name})"
                    raise OnexError(
                        code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=msg,
                        details=ModelErrorContext.with_context(
                            {
                                "pattern": ModelSchemaValue.from_value(pattern),
                                "priority": ModelSchemaValue.from_value(route.priority),
                                "route_name": ModelSchemaValue.from_value(
                                    route.route_name,
                                ),
                                "validation_type": ModelSchemaValue.from_value(
                                    "route_priority_uniqueness",
                                ),
                            },
                        ),
                    )
                priorities_seen.add(route.priority)

        return v

    @field_validator("trace_sampling_rate")
    @classmethod
    def validate_sampling_rate(cls, v: float) -> float:
        """Validate sampling rate is reasonable."""
        if v > 0.5:
            msg = "Trace sampling rate above 50% may impact performance"
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
                details=ModelErrorContext.with_context(
                    {
                        "sampling_rate": ModelSchemaValue.from_value(v),
                        "max_recommended": ModelSchemaValue.from_value(0.5),
                        "validation_type": ModelSchemaValue.from_value(
                            "sampling_rate_threshold",
                        ),
                    },
                ),
            )
        return v

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )
