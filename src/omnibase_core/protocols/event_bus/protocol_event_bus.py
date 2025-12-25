"""
ONEX event bus protocol for distributed messaging infrastructure.

This module provides the ProtocolEventBus protocol definition
for the main event bus interface. It combines Publisher, Subscriber,
and Lifecycle protocols following the Interface Segregation Principle (ISP).

Design Principles:
- Composed interface: Inherits from minimal Publisher, Subscriber, Lifecycle protocols
- ISP compliant: Components can depend on minimal interfaces they actually need
- Backwards compatible: Existing code using ProtocolEventBus continues to work
- Runtime checkable: Supports duck typing with @runtime_checkable

Usage:
    # Full event bus (publish + subscribe + lifecycle)
    def needs_full_bus(bus: ProtocolEventBus) -> None:
        pass

    # Only needs publishing
    from omnibase_core.protocols.event_bus import ProtocolEventBusPublisher
    def needs_publish_only(publisher: ProtocolEventBusPublisher) -> None:
        pass

    # Only needs subscription
    from omnibase_core.protocols.event_bus import ProtocolEventBusSubscriber
    def needs_subscribe_only(subscriber: ProtocolEventBusSubscriber) -> None:
        pass

    # Only needs lifecycle management
    from omnibase_core.protocols.event_bus import ProtocolEventBusLifecycle
    def needs_lifecycle_only(lifecycle: ProtocolEventBusLifecycle) -> None:
        pass
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.event_bus.protocol_event_bus_lifecycle import (
    ProtocolEventBusLifecycle,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_publisher import (
    ProtocolEventBusPublisher,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_subscriber import (
    ProtocolEventBusSubscriber,
)
from omnibase_core.protocols.event_bus.protocol_kafka_event_bus_adapter import (
    ProtocolKafkaEventBusAdapter,
)


@runtime_checkable
class ProtocolEventBus(
    ProtocolEventBusPublisher,
    ProtocolEventBusSubscriber,
    ProtocolEventBusLifecycle,
    Protocol,
):
    """
    ONEX event bus protocol for distributed messaging infrastructure.

    This is the full event bus interface that combines all capabilities:
    - Publishing: Methods from ProtocolEventBusPublisher
    - Subscribing: Methods from ProtocolEventBusSubscriber
    - Lifecycle: Methods from ProtocolEventBusLifecycle

    Implements the ONEX Messaging Design with environment isolation
    and node group mini-meshes.

    Interface Segregation:
        Components should depend on the minimal interface they need:
        - Use ProtocolEventBusPublisher for publish-only components
        - Use ProtocolEventBusSubscriber for subscribe-only components
        - Use ProtocolEventBusLifecycle for lifecycle management only
        - Use ProtocolEventBus only when you need all capabilities

    Example:
        >>> class MyService:
        ...     def __init__(self, bus: ProtocolEventBus):
        ...         self.bus = bus
        ...
        ...     async def start(self) -> None:
        ...         await self.bus.start()
        ...         await self.bus.subscribe("events", "my-group", self.handle)
        ...
        ...     async def handle(self, msg: ProtocolEventMessage) -> None:
        ...         # Process message
        ...         await self.bus.publish("results", None, b"done")
        ...
        ...     async def stop(self) -> None:
        ...         await self.bus.shutdown()
        ...         await self.bus.close()
    """

    @property
    def adapter(self) -> ProtocolKafkaEventBusAdapter:
        """
        Get the underlying Kafka adapter.

        Returns:
            The Kafka event bus adapter for low-level operations.
        """
        ...

    @property
    def environment(self) -> str:
        """
        Get the environment (dev, staging, prod).

        Returns:
            The current environment identifier.
        """
        ...

    @property
    def group(self) -> str:
        """
        Get the node group.

        Returns:
            The node group identifier for mini-mesh routing.
        """
        ...


__all__ = ["ProtocolEventBus"]
