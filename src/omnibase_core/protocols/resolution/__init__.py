# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Resolution Protocols for ONEX Dependency Resolution.

This module provides protocols for capability-based dependency resolution,
enabling auto-discovery and loose coupling between ONEX nodes.

Protocols:
    ProtocolDependencyResolver: Interface for resolving dependencies by
        capability, intent, or protocol rather than hardcoded module paths.

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

See Also:
    - OMN-1123: ModelDependencySpec (Capability-Based Dependencies)
    - ModelDependencySpec: The specification model for dependencies

.. versionadded:: 0.4.0
"""

from omnibase_core.protocols.resolution.protocol_dependency_resolver import (
    ProtocolDependencyResolver,
)

__all__ = [
    "ProtocolDependencyResolver",
]
