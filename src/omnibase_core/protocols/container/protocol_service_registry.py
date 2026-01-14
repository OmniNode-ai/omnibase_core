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

from omnibase_core.enums import EnumInjectionScope, EnumServiceLifecycle
from omnibase_core.protocols.base import (
    ContextValue,
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
    def config(self) -> ProtocolServiceRegistryConfig: ...

    @property
    def validator(self) -> ProtocolServiceValidator | None: ...

    @property
    def factory(self) -> ProtocolServiceFactory | None: ...

    async def register_service(
        self,
        interface: type[TInterface],
        implementation: type[TImplementation],
        lifecycle: EnumServiceLifecycle,
        scope: EnumInjectionScope,
        configuration: dict[str, ContextValue] | None = None,
    ) -> UUID: ...

    async def register_instance(
        self,
        interface: type[TInterface],
        instance: TInterface,
        scope: EnumInjectionScope = EnumInjectionScope.GLOBAL,
        metadata: dict[str, ContextValue] | None = None,
    ) -> UUID: ...

    async def register_factory(
        self,
        interface: type[TInterface],
        factory: ProtocolServiceFactory,
        lifecycle: EnumServiceLifecycle = EnumServiceLifecycle.TRANSIENT,
        scope: EnumInjectionScope = EnumInjectionScope.GLOBAL,
    ) -> UUID: ...

    async def unregister_service(self, registration_id: UUID) -> bool: ...

    async def resolve_service(
        self,
        interface: type[TInterface],
        scope: EnumInjectionScope | None = None,
        context: dict[str, ContextValue] | None = None,
    ) -> TInterface: ...

    async def resolve_named_service(
        self,
        interface: type[TInterface],
        name: str,
        scope: EnumInjectionScope | None = None,
    ) -> TInterface: ...

    async def resolve_all_services(
        self, interface: type[TInterface], scope: EnumInjectionScope | None = None
    ) -> list[TInterface]: ...

    async def try_resolve_service(
        self, interface: type[TInterface], scope: EnumInjectionScope | None = None
    ) -> TInterface | None: ...

    async def get_registration(
        self, registration_id: UUID
    ) -> ProtocolServiceRegistration | None: ...

    async def get_registrations_by_interface(
        self, interface: type[T]
    ) -> list[ProtocolServiceRegistration]: ...

    async def get_all_registrations(self) -> list[ProtocolServiceRegistration]: ...

    async def get_active_instances(
        self, registration_id: UUID | None = None
    ) -> list[ProtocolManagedServiceInstance]: ...

    async def dispose_instances(
        self, registration_id: UUID, scope: EnumInjectionScope | None = None
    ) -> int: ...

    async def validate_registration(
        self, registration: ProtocolServiceRegistration
    ) -> bool: ...

    async def detect_circular_dependencies(
        self, registration: ProtocolServiceRegistration
    ) -> list[UUID]: ...

    async def get_dependency_graph(
        self, service_id: UUID
    ) -> ProtocolDependencyGraph | None: ...

    async def get_registry_status(self) -> ProtocolServiceRegistryStatus: ...

    async def validate_service_health(
        self, registration_id: UUID
    ) -> ProtocolValidationResult: ...

    async def update_service_configuration(
        self, registration_id: UUID, configuration: dict[str, ContextValue]
    ) -> bool: ...

    async def create_injection_scope(
        self, scope_name: str, parent_scope: UUID | None = None
    ) -> UUID: ...

    async def dispose_injection_scope(self, scope_id: UUID) -> int: ...

    async def get_injection_context(
        self, context_id: UUID
    ) -> ProtocolInjectionContext | None: ...


__all__ = ["ProtocolServiceRegistry"]
