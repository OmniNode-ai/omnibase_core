# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolDependencyGraph": (
        "omnibase_core.protocols.container.protocol_dependency_graph",
        "ProtocolDependencyGraph",
    ),
    "ProtocolInjectionContext": (
        "omnibase_core.protocols.container.protocol_injection_context",
        "ProtocolInjectionContext",
    ),
    "ProtocolManagedServiceInstance": (
        "omnibase_core.protocols.container.protocol_managed_service_instance",
        "ProtocolManagedServiceInstance",
    ),
    "ProtocolServiceDependency": (
        "omnibase_core.protocols.container.protocol_service_dependency",
        "ProtocolServiceDependency",
    ),
    "ProtocolServiceFactory": (
        "omnibase_core.protocols.container.protocol_service_factory",
        "ProtocolServiceFactory",
    ),
    "ProtocolServiceRegistration": (
        "omnibase_core.protocols.container.protocol_service_registration",
        "ProtocolServiceRegistration",
    ),
    "ProtocolServiceRegistrationMetadata": (
        "omnibase_core.protocols.container.protocol_service_registration_metadata",
        "ProtocolServiceRegistrationMetadata",
    ),
    "ProtocolServiceRegistry": (
        "omnibase_core.protocols.container.protocol_service_registry",
        "ProtocolServiceRegistry",
    ),
    "ProtocolServiceRegistryConfig": (
        "omnibase_core.protocols.container.protocol_service_registry_config",
        "ProtocolServiceRegistryConfig",
    ),
    "ProtocolServiceRegistryStatus": (
        "omnibase_core.protocols.container.protocol_service_registry_status",
        "ProtocolServiceRegistryStatus",
    ),
    "ProtocolServiceValidator": (
        "omnibase_core.protocols.container.protocol_service_validator",
        "ProtocolServiceValidator",
    ),
    "ProtocolValidationResult": (
        "omnibase_core.protocols.container.protocol_validation_result",
        "ProtocolValidationResult",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
