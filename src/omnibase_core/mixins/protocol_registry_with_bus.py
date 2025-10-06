from __future__ import annotations

"""
Protocol for registry that provides event bus.
"""


from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from omnibase_spi.protocols.event_bus.protocol_event_bus_mixin import (
        ProtocolAsyncEventBus,
    )


class RegistryWithBus(Protocol):
    """Protocol for registry that provides event bus."""

    event_bus: (
        ProtocolAsyncEventBus | None
    )  # ProtocolAsyncEventBus includes sync capabilities
