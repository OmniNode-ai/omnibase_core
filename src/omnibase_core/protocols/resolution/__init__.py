"""
Resolution Protocols for ONEX Dependency Resolution.

This module provides protocols for capability-based dependency resolution,
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

__all__ = [
    "ProtocolCapabilityResolver",
    "ProtocolDependencyResolver",
    "ProtocolExecutionResolver",
    "ProtocolProfile",
    "ProtocolProviderRegistry",
]
