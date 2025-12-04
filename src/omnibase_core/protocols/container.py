"""
Core-native container and service registry protocols.

This module provides protocol definitions for dependency injection,
service registry, and container management. These are Core-native
equivalents of the SPI container protocols.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol, Type, runtime_checkable

from omnibase_core.protocols.base import (
    ContextValue,
    LiteralHealthStatus,
    LiteralInjectionScope,
    LiteralOperationStatus,
    LiteralServiceLifecycle,
    LiteralServiceResolutionStatus,
    ProtocolDateTime,
    ProtocolSemVer,
    T,
    TImplementation,
    TInterface,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# Service Health Status (alias for health status in registry context)
# =============================================================================

ServiceHealthStatus = LiteralHealthStatus


# =============================================================================
# Service Registration Metadata Protocol
# =============================================================================


@runtime_checkable
class ProtocolServiceRegistrationMetadata(Protocol):
    """
    Protocol for service registration metadata objects.

    Contains comprehensive metadata about a registered service including
    identification, versioning, and configuration.
    """

    service_id: str
    service_name: str
    service_interface: str
    service_implementation: str
    version: ProtocolSemVer
    description: str | None
    tags: list[str]
    configuration: dict[str, ContextValue]
    created_at: ProtocolDateTime
    last_modified_at: ProtocolDateTime | None


# =============================================================================
# Service Dependency Protocol
# =============================================================================


@runtime_checkable
class ProtocolServiceDependency(Protocol):
    """
    Protocol for service dependency information.

    Defines the interface for service dependency metadata including
    version constraints, circular dependency detection, and injection points.
    """

    dependency_name: str
    dependency_interface: str
    dependency_version: ProtocolSemVer | None
    is_required: bool
    is_circular: bool
    injection_point: str
    default_value: Any | None
    metadata: dict[str, ContextValue]

    async def validate_dependency(self) -> bool:
        """Validate that dependency constraints are satisfied."""
        ...

    def is_satisfied(self) -> bool:
        """Check if dependency requirements are currently met."""
        ...


# =============================================================================
# Service Registration Protocol
# =============================================================================


@runtime_checkable
class ProtocolServiceRegistration(Protocol):
    """
    Protocol for service registration information.

    Defines the interface for comprehensive service registration metadata
    including lifecycle management, dependency tracking, and health monitoring.
    """

    registration_id: str
    service_metadata: ProtocolServiceRegistrationMetadata
    lifecycle: LiteralServiceLifecycle
    scope: LiteralInjectionScope
    dependencies: list[ProtocolServiceDependency]
    registration_status: Literal[
        "registered", "unregistered", "failed", "pending", "conflict", "invalid"
    ]
    health_status: ServiceHealthStatus
    registration_time: ProtocolDateTime
    last_access_time: ProtocolDateTime | None
    access_count: int
    instance_count: int
    max_instances: int | None

    async def validate_registration(self) -> bool:
        """Validate that registration is valid and complete."""
        ...

    def is_active(self) -> bool:
        """Check if this registration is currently active."""
        ...


# =============================================================================
# Service Instance Protocol
# =============================================================================


@runtime_checkable
class ProtocolServiceInstance(Protocol):
    """
    Protocol for service registry managed instance information.

    Represents an active instance of a registered service with
    lifecycle and usage tracking.
    """

    instance_id: str
    service_registration_id: str
    instance: Any
    lifecycle: LiteralServiceLifecycle
    scope: LiteralInjectionScope
    created_at: ProtocolDateTime
    last_accessed: ProtocolDateTime
    access_count: int
    is_disposed: bool
    metadata: dict[str, ContextValue]

    async def validate_instance(self) -> bool:
        """Validate that instance is valid and ready."""
        ...

    def is_active(self) -> bool:
        """Check if instance is currently active."""
        ...


# =============================================================================
# Dependency Graph Protocol
# =============================================================================


@runtime_checkable
class ProtocolDependencyGraph(Protocol):
    """
    Protocol for dependency graph information.

    Defines the interface for dependency graph analysis including
    dependency chains, circular reference detection, and resolution ordering.
    """

    service_id: str
    dependencies: list[str]
    dependents: list[str]
    depth_level: int
    circular_references: list[str]
    resolution_order: list[str]
    metadata: dict[str, ContextValue]


# =============================================================================
# Injection Context Protocol
# =============================================================================


@runtime_checkable
class ProtocolInjectionContext(Protocol):
    """
    Protocol for dependency injection context.

    Defines the interface for injection context tracking including
    resolution status, error handling, and dependency path tracking.
    """

    context_id: str
    target_service_id: str
    scope: LiteralInjectionScope
    resolved_dependencies: dict[str, ContextValue]
    injection_time: ProtocolDateTime
    resolution_status: LiteralServiceResolutionStatus
    error_details: str | None
    resolution_path: list[str]
    metadata: dict[str, ContextValue]


# =============================================================================
# Service Registry Status Protocol
# =============================================================================


@runtime_checkable
class ProtocolServiceRegistryStatus(Protocol):
    """
    Protocol for service registry status information.

    Defines the interface for comprehensive registry status reporting
    including registration statistics, health monitoring, and performance metrics.
    """

    registry_id: str
    status: LiteralOperationStatus
    message: str
    total_registrations: int
    active_instances: int
    failed_registrations: int
    circular_dependencies: int
    lifecycle_distribution: dict[LiteralServiceLifecycle, int]
    scope_distribution: dict[LiteralInjectionScope, int]
    health_summary: dict[ServiceHealthStatus, int]
    memory_usage_bytes: int | None
    average_resolution_time_ms: float | None
    last_updated: ProtocolDateTime


# =============================================================================
# Service Validator Protocol
# =============================================================================


@runtime_checkable
class ProtocolServiceValidator(Protocol):
    """
    Protocol for service validation operations.

    Defines the interface for comprehensive service validation including
    interface compliance checking and dependency validation.
    """

    async def validate_service(
        self, service: Any, interface: Type[Any]
    ) -> ProtocolValidationResult:
        """Validate that a service implementation conforms to its interface."""
        ...

    async def validate_dependencies(
        self, dependencies: list[ProtocolServiceDependency]
    ) -> ProtocolValidationResult:
        """Validate that all dependencies can be satisfied."""
        ...


# =============================================================================
# Service Factory Protocol
# =============================================================================


@runtime_checkable
class ProtocolServiceFactory(Protocol):
    """
    Protocol for service factory operations.

    Defines the interface for service instance creation with dependency
    injection support and lifecycle management.
    """

    async def create_instance(
        self, interface: Type[T], context: dict[str, ContextValue]
    ) -> T:
        """Create a new service instance with dependency injection."""
        ...

    async def dispose_instance(self, instance: Any) -> None:
        """Dispose of a service instance."""
        ...


# =============================================================================
# Service Registry Config Protocol
# =============================================================================


@runtime_checkable
class ProtocolServiceRegistryConfig(Protocol):
    """
    Protocol for service registry configuration.

    Defines the interface for comprehensive service registry configuration
    including auto-wiring, lazy loading, and monitoring settings.
    """

    registry_name: str
    auto_wire_enabled: bool
    lazy_loading_enabled: bool
    circular_dependency_detection: bool
    max_resolution_depth: int
    instance_pooling_enabled: bool
    health_monitoring_enabled: bool
    performance_monitoring_enabled: bool
    configuration: dict[str, ContextValue]


# =============================================================================
# Service Registry Protocol
# =============================================================================


@runtime_checkable
class ProtocolServiceRegistry(Protocol):
    """
    Protocol for service registry operations.

    Provides dependency injection service registration and management.
    Supports the complete service lifecycle including registration,
    resolution, injection, and disposal.
    """

    @property
    def config(self) -> ProtocolServiceRegistryConfig:
        """Get registry configuration."""
        ...

    @property
    def validator(self) -> ProtocolServiceValidator | None:
        """Get optional service validator."""
        ...

    @property
    def factory(self) -> ProtocolServiceFactory | None:
        """Get optional service factory."""
        ...

    async def register_service(
        self,
        interface: Type[TInterface],
        implementation: Type[TImplementation],
        lifecycle: LiteralServiceLifecycle,
        scope: LiteralInjectionScope,
        configuration: dict[str, ContextValue] | None = None,
    ) -> str:
        """Register a service implementation."""
        ...

    async def register_instance(
        self,
        interface: Type[TInterface],
        instance: TInterface,
        scope: LiteralInjectionScope = "global",
        metadata: dict[str, ContextValue] | None = None,
    ) -> str:
        """Register an existing instance."""
        ...

    async def register_factory(
        self,
        interface: Type[TInterface],
        factory: ProtocolServiceFactory,
        lifecycle: LiteralServiceLifecycle = "transient",
        scope: LiteralInjectionScope = "global",
    ) -> str:
        """Register a service factory."""
        ...

    async def unregister_service(self, registration_id: str) -> bool:
        """Unregister a service."""
        ...

    async def resolve_service(
        self,
        interface: Type[TInterface],
        scope: LiteralInjectionScope | None = None,
        context: dict[str, ContextValue] | None = None,
    ) -> TInterface:
        """Resolve a service by interface."""
        ...

    async def resolve_named_service(
        self,
        interface: Type[TInterface],
        name: str,
        scope: LiteralInjectionScope | None = None,
    ) -> TInterface:
        """Resolve a named service."""
        ...

    async def resolve_all_services(
        self, interface: Type[TInterface], scope: LiteralInjectionScope | None = None
    ) -> list[TInterface]:
        """Resolve all services matching interface."""
        ...

    async def try_resolve_service(
        self, interface: Type[TInterface], scope: LiteralInjectionScope | None = None
    ) -> TInterface | None:
        """Try to resolve a service, returning None if not found."""
        ...

    async def get_registration(
        self, registration_id: str
    ) -> ProtocolServiceRegistration | None:
        """Get registration by ID."""
        ...

    async def get_registrations_by_interface(
        self, interface: Type[T]
    ) -> list[ProtocolServiceRegistration]:
        """Get all registrations for an interface."""
        ...

    async def get_all_registrations(self) -> list[ProtocolServiceRegistration]:
        """Get all registrations."""
        ...

    async def get_active_instances(
        self, registration_id: str | None = None
    ) -> list[ProtocolServiceInstance]:
        """Get active instances."""
        ...

    async def dispose_instances(
        self, registration_id: str, scope: LiteralInjectionScope | None = None
    ) -> int:
        """Dispose instances for a registration."""
        ...

    async def validate_registration(
        self, registration: ProtocolServiceRegistration
    ) -> bool:
        """Validate a registration."""
        ...

    async def detect_circular_dependencies(
        self, registration: ProtocolServiceRegistration
    ) -> list[str]:
        """Detect circular dependencies."""
        ...

    async def get_dependency_graph(
        self, service_id: str
    ) -> ProtocolDependencyGraph | None:
        """Get dependency graph for a service."""
        ...

    async def get_registry_status(self) -> ProtocolServiceRegistryStatus:
        """Get registry status."""
        ...

    async def validate_service_health(
        self, registration_id: str
    ) -> ProtocolValidationResult:
        """Validate service health."""
        ...

    async def update_service_configuration(
        self, registration_id: str, configuration: dict[str, ContextValue]
    ) -> bool:
        """Update service configuration."""
        ...

    async def create_injection_scope(
        self, scope_name: str, parent_scope: str | None = None
    ) -> str:
        """Create a new injection scope."""
        ...

    async def dispose_injection_scope(self, scope_id: str) -> int:
        """Dispose an injection scope."""
        ...

    async def get_injection_context(
        self, context_id: str
    ) -> ProtocolInjectionContext | None:
        """Get injection context."""
        ...


# =============================================================================
# Validation Result Protocol (forward declaration for container module)
# =============================================================================


@runtime_checkable
class ProtocolValidationResult(Protocol):
    """
    Protocol for validation result objects.

    Forward declaration to avoid circular imports with validation module.
    See validation.py for the complete definition.
    """

    is_valid: bool
    protocol_name: str
    implementation_name: str
    errors: list[Any]  # ProtocolValidationError
    warnings: list[Any]  # ProtocolValidationError

    def add_error(
        self,
        error_type: str,
        message: str,
        context: dict[str, ContextValue] | None = None,
        severity: str | None = None,
    ) -> None:
        """Add an error to the result."""
        ...

    def add_warning(
        self,
        error_type: str,
        message: str,
        context: dict[str, ContextValue] | None = None,
    ) -> None:
        """Add a warning to the result."""
        ...

    async def get_summary(self) -> str:
        """Get result summary."""
        ...


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Health Status
    "ServiceHealthStatus",
    # Protocols
    "ProtocolServiceRegistrationMetadata",
    "ProtocolServiceDependency",
    "ProtocolServiceRegistration",
    "ProtocolServiceInstance",
    "ProtocolDependencyGraph",
    "ProtocolInjectionContext",
    "ProtocolServiceRegistryStatus",
    "ProtocolServiceValidator",
    "ProtocolServiceFactory",
    "ProtocolServiceRegistryConfig",
    "ProtocolServiceRegistry",
    "ProtocolValidationResult",
]
