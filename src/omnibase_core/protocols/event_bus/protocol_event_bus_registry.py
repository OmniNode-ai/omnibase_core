"""
Protocol for registry that provides event bus access.

This module provides the ProtocolEventBusRegistry protocol definition
for service registries with event bus access.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.event_bus.protocol_event_bus_base import (
    ProtocolEventBusBase,
)


@runtime_checkable
class ProtocolEventBusRegistry(Protocol):
    """
    Protocol for registry that provides event bus access.

    Defines interface for service registries that provide access
    to event bus instances for dependency injection.
    """

    event_bus: ProtocolEventBusBase | None

    async def validate_registry_bus(self) -> bool:
        """Validate that the registry has a valid event bus."""
        ...

    def has_bus_access(self) -> bool:
        """Check if the registry has bus access."""
        ...


__all__ = ["ProtocolEventBusRegistry"]
