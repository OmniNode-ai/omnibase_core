"""
Routing Subcontract Model - ONEX Microservices ModelArchitecture Compliant.



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

Strict typing is enforced: No Any types allowed in implementation.
"""

import threading
from typing import Any, ClassVar, Literal, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.constants import TIMEOUT_LONG_MS
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.models.configuration.model_circuit_breaker_metadata import (
    ModelCircuitBreakerMetadata,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_load_balancing import ModelLoadBalancing
from .model_request_transformation import ModelRequestTransformation
from .model_route_definition import ModelRouteDefinition
from .model_routing_metrics import ModelRoutingMetrics

# Lazy model rebuild flag - forward references are resolved on first use, not at import
_models_rebuilt = False
_rebuild_lock = threading.Lock()


def _ensure_models_rebuilt(
    routing_subcontract_cls: type[BaseModel] | None = None,
) -> None:
    """Ensure models are rebuilt to resolve forward references (lazy initialization).

    This function implements lazy model rebuild to avoid importing ModelCustomFields
    at module load time. The rebuild only happens on first ModelRoutingSubcontract
    instantiation, improving import performance when the model isn't used.

    The pattern:
    1. Module-level flag tracks if rebuild has occurred
    2. This function is called via __new__ on first instantiation
    3. The rebuild resolves ModelCircuitBreakerMetadata's forward reference to ModelCustomFields
    4. Then rebuilds ModelCircuitBreaker to pick up the resolved metadata type
    5. Then rebuilds ModelRoutingSubcontract to pick up the resolved circuit breaker type
    6. Subsequent instantiations skip the rebuild (flag is already True)

    Args:
        routing_subcontract_cls: The ModelRoutingSubcontract class to rebuild. Must be
            provided on first call to properly resolve the forward reference chain.

    Thread Safety:
        This function is thread-safe. It uses double-checked locking to ensure that
        concurrent first-instantiation calls safely coordinate the rebuild. The pattern:
        1. Fast path: Check flag without lock (subsequent calls return immediately)
        2. Acquire lock only when rebuild might be needed
        3. Re-check flag inside lock to handle race conditions
        4. Perform rebuild and set flag atomically within lock
    """
    global _models_rebuilt
    if _models_rebuilt:  # Fast path - no lock needed
        return

    with _rebuild_lock:
        if (
            _models_rebuilt
        ):  # Double-check after acquiring lock  # type: ignore[unreachable]
            return  # type: ignore[unreachable]

        from omnibase_core.models.services.model_custom_fields import (  # noqa: F401
            ModelCustomFields,
        )

        # First rebuild the metadata model to resolve its forward reference
        ModelCircuitBreakerMetadata.model_rebuild()
        # Then rebuild the circuit breaker model to pick up the resolved metadata
        ModelCircuitBreaker.model_rebuild()
        # Finally rebuild the routing subcontract to pick up the resolved circuit breaker
        if routing_subcontract_cls is not None:
            routing_subcontract_cls.model_rebuild()
        _models_rebuilt = True


class ModelRoutingSubcontract(BaseModel):
    """
    ONEX Microservices Routing subcontract model for request routing functionality.

    Comprehensive routing subcontract providing route definitions,
    load balancing, circuit breaking, and request transformation optimized
    for ONEX microservices ecosystem. Designed for composition into node
    contracts requiring routing functionality with service mesh integration.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    def __new__(cls, **_data: Any) -> "ModelRoutingSubcontract":
        """Override __new__ to trigger lazy model rebuild before Pydantic validation.

        Pydantic validates model completeness before calling model_validator,
        so we must trigger the rebuild in __new__ which runs first.

        Args:
            **_data: Keyword arguments passed to Pydantic (handled by __init__).
        """
        _ensure_models_rebuilt(cls)
        return super().__new__(cls)

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: Literal["allow", "ignore", "forbid"] | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        """Override to ensure model rebuild before validation.

        This ensures forward references are resolved when deserializing
        nested structures via model_validate(). The rebuild is triggered
        before Pydantic validation to ensure all forward references in the
        model hierarchy (ModelCircuitBreakerMetadata -> ModelCustomFields ->
        ModelCircuitBreaker -> ModelRoutingSubcontract) are properly resolved.

        Args:
            obj: Object to validate (dict, model instance, etc.).
            strict: Whether to enforce strict validation.
            extra: How to handle extra fields ('allow', 'ignore', 'forbid').
            from_attributes: Whether to extract data from object attributes.
            context: Additional context for validation.
            by_alias: Whether to use field aliases for validation.
            by_name: Whether to use field names for validation.

        Returns:
            Validated ModelRoutingSubcontract instance.
        """
        _ensure_models_rebuilt(cls)
        cls.model_rebuild()
        return super().model_validate(
            obj,
            strict=strict,
            extra=extra,
            from_attributes=from_attributes,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

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
        default_factory=lambda: ModelLoadBalancing(
            version=ModelSemVer(major=1, minor=0, patch=0)
        ),
        description="Load balancing configuration",
    )

    # Circuit breaker configuration
    circuit_breaker: ModelCircuitBreaker = Field(
        default_factory=ModelCircuitBreaker,
        description="Circuit breaker configuration",
    )

    # Request/Response transformation
    transformation: ModelRequestTransformation = Field(
        default_factory=lambda: ModelRequestTransformation(
            version=ModelSemVer(major=1, minor=0, patch=0)
        ),
        description="Request transformation configuration",
    )

    # Routing metrics and monitoring
    metrics: ModelRoutingMetrics = Field(
        default_factory=lambda: ModelRoutingMetrics(
            version=ModelSemVer(major=1, minor=0, patch=0)
        ),
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
        default=TIMEOUT_LONG_MS,
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

    @model_validator(mode="after")
    def validate_route_priorities_unique(self) -> "ModelRoutingSubcontract":
        """Validate that route priorities are unique within same pattern."""
        # Group routes by pattern to check priority uniqueness within each pattern
        pattern_routes: dict[str, list[ModelRouteDefinition]] = {}

        for route in self.routes:
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
                    raise ModelOnexError(
                        message=msg,
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        pattern=pattern,
                        priority=route.priority,
                        route_name=route.route_name,
                        validation_type="route_priority_uniqueness",
                    )
                priorities_seen.add(route.priority)

        return self

    @model_validator(mode="after")
    def validate_sampling_rate(self) -> "ModelRoutingSubcontract":
        """Validate sampling rate is reasonable."""
        if self.trace_sampling_rate > 0.5:
            msg = "Trace sampling rate above 50% may impact performance"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                sampling_rate=self.trace_sampling_rate,
                max_recommended=0.5,
                validation_type="sampling_rate_threshold",
            )
        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )
