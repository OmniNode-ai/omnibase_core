"""
Protocol for service registry operations.

This module provides the ProtocolServiceRegistry protocol which
provides dependency injection service registration and management.
Supports the complete service lifecycle including registration,
resolution, injection, and disposal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable
from uuid import UUID

from omnibase_core.protocols.base import (
    ContextValue,
    LiteralInjectionScope,
    LiteralServiceLifecycle,
)

if TYPE_CHECKING:
    from omnibase_core.protocols.container.protocol_dependency_graph import (
        ProtocolDependencyGraph,
    )
    from omnibase_core.protocols.container.protocol_injection_context import (
        ProtocolInjectionContext,
    )
    from omnibase_core.protocols.container.protocol_managed_service_instance import (
        ProtocolManagedServiceInstance,
    )
    from omnibase_core.protocols.container.protocol_service_factory import (
        ProtocolServiceFactory,
    )
    from omnibase_core.protocols.container.protocol_service_registration import (
        ProtocolServiceRegistration,
    )
    from omnibase_core.protocols.container.protocol_service_registry_config import (
        ProtocolServiceRegistryConfig,
    )
    from omnibase_core.protocols.container.protocol_service_registry_status import (
        ProtocolServiceRegistryStatus,
    )
    from omnibase_core.protocols.container.protocol_service_validator import (
        ProtocolServiceValidator,
    )
    from omnibase_core.protocols.container.protocol_validation_result import (
        ProtocolValidationResult,
    )

T = TypeVar("T")
TInterface = TypeVar("TInterface")
TImplementation = TypeVar("TImplementation")


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
        interface: type[TInterface],
        implementation: type[TImplementation],
        lifecycle: LiteralServiceLifecycle,
        scope: LiteralInjectionScope,
        configuration: dict[str, ContextValue] | None = None,
    ) -> UUID:
        """Register a service implementation."""
        ...

    async def register_instance(
        self,
        interface: type[TInterface],
        instance: TInterface,
        scope: LiteralInjectionScope = "global",
        metadata: dict[str, ContextValue] | None = None,
    ) -> UUID:
        """Register an existing instance."""
        ...

    async def register_factory(
        self,
        interface: type[TInterface],
        factory: ProtocolServiceFactory,
        lifecycle: LiteralServiceLifecycle = "transient",
        scope: LiteralInjectionScope = "global",
    ) -> UUID:
        """Register a service factory."""
        ...

    async def unregister_service(self, registration_id: UUID) -> bool:
        """Unregister a service."""
        ...

    async def resolve_service(
        self,
        interface: type[TInterface],
        scope: LiteralInjectionScope | None = None,
        context: dict[str, ContextValue] | None = None,
    ) -> TInterface:
        """Resolve a service by interface."""
        ...

    async def resolve_named_service(
        self,
        interface: type[TInterface],
        name: str,
        scope: LiteralInjectionScope | None = None,
    ) -> TInterface:
        """Resolve a named service."""
        ...

    async def resolve_all_services(
        self, interface: type[TInterface], scope: LiteralInjectionScope | None = None
    ) -> list[TInterface]:
        """Resolve all services matching interface."""
        ...

    async def try_resolve_service(
        self, interface: type[TInterface], scope: LiteralInjectionScope | None = None
    ) -> TInterface | None:
        """Try to resolve a service, returning None if not found."""
        ...

    async def get_registration(
        self, registration_id: UUID
    ) -> ProtocolServiceRegistration | None:
        """Get registration by ID."""
        ...

    async def get_registrations_by_interface(
        self, interface: type[T]
    ) -> list[ProtocolServiceRegistration]:
        """Get all registrations for an interface."""
        ...

    async def get_all_registrations(self) -> list[ProtocolServiceRegistration]:
        """Get all registrations."""
        ...

    async def get_active_instances(
        self, registration_id: UUID | None = None
    ) -> list[ProtocolManagedServiceInstance]:
        """Get active instances."""
        ...

    async def dispose_instances(
        self, registration_id: UUID, scope: LiteralInjectionScope | None = None
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
    ) -> list[UUID]:
        """Detect circular dependencies."""
        ...

    async def get_dependency_graph(
        self, service_id: UUID
    ) -> ProtocolDependencyGraph | None:
        """Get dependency graph for a service."""
        ...

    async def get_registry_status(self) -> ProtocolServiceRegistryStatus:
        """Get registry status."""
        ...

    async def validate_service_health(
        self, registration_id: UUID
    ) -> ProtocolValidationResult:
        """Validate service health."""
        ...

    async def update_service_configuration(
        self, registration_id: UUID, configuration: dict[str, ContextValue]
    ) -> bool:
        """Update service configuration."""
        ...

    async def create_injection_scope(
        self, scope_name: str, parent_scope: UUID | None = None
    ) -> UUID:
        """Create a new injection scope."""
        ...

    async def dispose_injection_scope(self, scope_id: UUID) -> int:
        """Dispose an injection scope."""
        ...

    async def get_injection_context(
        self, context_id: UUID
    ) -> ProtocolInjectionContext | None:
        """Get injection context."""
        ...


__all__ = ["ProtocolServiceRegistry"]
