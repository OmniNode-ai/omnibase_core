"""
Core-native container and service registry protocols.

This package provides protocol definitions for dependency injection,
service registry, and container management. These are Core-native
equivalents of the SPI container protocols.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
- Single class per file: Each protocol in its own module

Usage:
    from omnibase_core.protocols.container import (
        ProtocolServiceRegistry,
        ProtocolServiceRegistration,
        ProtocolManagedServiceInstance,
    )
"""

from omnibase_core.protocols.container.protocol_dependency_graph import (
    ProtocolDependencyGraph,
)
from omnibase_core.protocols.container.protocol_injection_context import (
    ProtocolInjectionContext,
)
from omnibase_core.protocols.container.protocol_managed_service_instance import (
    ProtocolManagedServiceInstance,
)
from omnibase_core.protocols.container.protocol_service_dependency import (
    ProtocolServiceDependency,
)
from omnibase_core.protocols.container.protocol_service_factory import (
    ProtocolServiceFactory,
)
from omnibase_core.protocols.container.protocol_service_registration import (
    ProtocolServiceRegistration,
)
from omnibase_core.protocols.container.protocol_service_registration_metadata import (
    ProtocolServiceRegistrationMetadata,
)
from omnibase_core.protocols.container.protocol_service_registry import (
    ProtocolServiceRegistry,
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

__all__ = [
    # Protocols
    "ProtocolServiceRegistrationMetadata",
    "ProtocolServiceDependency",
    "ProtocolServiceRegistration",
    "ProtocolManagedServiceInstance",
    "ProtocolDependencyGraph",
    "ProtocolInjectionContext",
    "ProtocolServiceRegistryStatus",
    "ProtocolServiceValidator",
    "ProtocolServiceFactory",
    "ProtocolServiceRegistryConfig",
    "ProtocolServiceRegistry",
    "ProtocolValidationResult",
]
