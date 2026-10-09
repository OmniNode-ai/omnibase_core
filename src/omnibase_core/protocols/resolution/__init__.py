# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Resolution Protocols for ONEX Dependency Resolution.

Protocols for capability-based dependency resolution,
enabling auto-discovery and loose coupling between ONEX nodes.

Protocols:
    ProtocolDependencyResolver: Interface for resolving dependencies by
        capability, intent, or protocol rather than hardcoded module paths.
    ProtocolCapabilityResolver: Interface for resolving capability dependencies
        to concrete provider bindings.
    ProtocolExecutionResolver: Interface for resolving handler execution order
        from profiles and contracts.
    ProtocolProviderRegistry: Minimal interface for provider registry
        (stub for OMN-1156).

Usage:
    .. code-block:: python

        from omnibase_core.protocols.resolution import ProtocolDependencyResolver
        from omnibase_core.models.contracts import ModelDependencySpec

        async def get_event_bus(resolver: ProtocolDependencyResolver) -> Any:
            spec = ModelDependencySpec(
                name="event_bus",
                type="protocol",
                capability="event.publishing",
            )
            return await resolver.resolve(spec)

    Capability-based resolution:

    .. code-block:: python

        from omnibase_core.protocols.resolution import (
            ProtocolCapabilityResolver,
            ProtocolProviderRegistry,
        )
        from omnibase_core.models.capabilities import ModelCapabilityDependency

        def resolve_database(
            resolver: ProtocolCapabilityResolver,
            registry: ProtocolProviderRegistry,
        ) -> ModelBinding:
            dep = ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
            )
            return resolver.resolve(dep, registry)

See Also:
    - OMN-1123: ModelDependencySpec (Capability-Based Dependencies)
    - OMN-1152: ModelCapabilityDependency (Vendor-Agnostic Dependencies)
    - OMN-1155: ProtocolCapabilityResolver (This protocol)
    - OMN-1156: ProtocolProviderRegistry (Provider Registry Protocol)
    - ModelDependencySpec: The specification model for dependencies

.. versionadded:: 0.4.0
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.resolution.protocol_capability_resolver import (
        ProtocolCapabilityResolver,
        ProtocolProfile,
        ProtocolProviderRegistry,
    )
    from omnibase_core.protocols.resolution.protocol_dependency_resolver import (
        ProtocolDependencyResolver,
    )
    from omnibase_core.protocols.resolution.protocol_execution_resolver import (
        ProtocolExecutionResolver,
    )
    from omnibase_core.protocols.resolution.protocol_tiered_resolver import (
        ProtocolTieredResolver,
    )

__all__ = [
    "ProtocolCapabilityResolver",
    "ProtocolDependencyResolver",
    "ProtocolExecutionResolver",
    "ProtocolProfile",
    "ProtocolProviderRegistry",
    "ProtocolTieredResolver",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolCapabilityResolver": (
        "omnibase_core.protocols.resolution.protocol_capability_resolver",
        "ProtocolCapabilityResolver",
    ),
    "ProtocolProfile": (
        "omnibase_core.protocols.resolution.protocol_capability_resolver",
        "ProtocolProfile",
    ),
    "ProtocolProviderRegistry": (
        "omnibase_core.protocols.resolution.protocol_capability_resolver",
        "ProtocolProviderRegistry",
    ),
    "ProtocolDependencyResolver": (
        "omnibase_core.protocols.resolution.protocol_dependency_resolver",
        "ProtocolDependencyResolver",
    ),
    "ProtocolExecutionResolver": (
        "omnibase_core.protocols.resolution.protocol_execution_resolver",
        "ProtocolExecutionResolver",
    ),
    "ProtocolTieredResolver": (
        "omnibase_core.protocols.resolution.protocol_tiered_resolver",
        "ProtocolTieredResolver",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
