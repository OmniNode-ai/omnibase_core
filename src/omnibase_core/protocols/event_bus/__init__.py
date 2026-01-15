"""
Core-native event bus protocols.

This module provides protocol definitions for event-driven messaging,
event bus operations, and event envelope handling. These are Core-native
equivalents of the SPI event bus protocols.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
- Interface Segregation: Separate protocols for publish, subscribe, lifecycle

ISP-Compliant Protocols:
    The event bus protocols follow the Interface Segregation Principle (ISP).
    Components should depend on the minimal interface they need:

    - ProtocolEventBusPublisher: For components that only publish events
    - ProtocolEventBusSubscriber: For components that only subscribe to events
    - ProtocolEventBusLifecycle: For components that manage lifecycle
    - ProtocolEventBus: Full interface combining all capabilities

Example:
    >>> # Import only what you need
    >>> from omnibase_core.protocols.event_bus import ProtocolEventBusPublisher
    >>>
    >>> class MyPublisher:
    ...     def __init__(self, publisher: ProtocolEventBusPublisher):
    ...         self.publisher = publisher
    ...
    ...     async def emit(self, data: bytes) -> None:
    ...         await self.publisher.publish("my.topic", None, data)
"""

from __future__ import annotations

from omnibase_core.protocols.event_bus.protocol_async_event_bus import (
    ProtocolAsyncEventBus,
)
from omnibase_core.protocols.event_bus.protocol_event_bus import ProtocolEventBus
from omnibase_core.protocols.event_bus.protocol_event_bus_base import (
    ProtocolEventBusBase,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_headers import (
    ProtocolEventBusHeaders,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_lifecycle import (
    ProtocolEventBusLifecycle,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_listener import (
    ProtocolEventBusListener,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_log_emitter import (
    ProtocolEventBusLogEmitter,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_publisher import (
    ProtocolEventBusPublisher,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_registry import (
    ProtocolEventBusRegistry,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_subscriber import (
    ProtocolEventBusSubscriber,
)
from omnibase_core.protocols.event_bus.protocol_event_envelope import (
    ProtocolEventEnvelope,
)
from omnibase_core.protocols.event_bus.protocol_event_message import (
    ProtocolEventMessage,
)
from omnibase_core.protocols.event_bus.protocol_from_event import ProtocolFromEvent
from omnibase_core.protocols.event_bus.protocol_kafka_event_bus_adapter import (
    ProtocolKafkaEventBusAdapter,
)
from omnibase_core.protocols.event_bus.protocol_sync_event_bus import (
    ProtocolSyncEventBus,
)

__all__ = [
    # Event Message
    "ProtocolEventMessage",
    # Headers
    "ProtocolEventBusHeaders",
    # Adapters
    "ProtocolKafkaEventBusAdapter",
    # Event Bus - ISP-compliant protocols (prefer these for minimal dependencies)
    "ProtocolEventBusPublisher",
    "ProtocolEventBusSubscriber",
    "ProtocolEventBusLifecycle",
    "ProtocolEventBusListener",
    # Event Bus - Full interface (combines Publisher, Subscriber, Lifecycle)
    "ProtocolEventBus",
    "ProtocolEventBusBase",
    "ProtocolSyncEventBus",
    "ProtocolAsyncEventBus",
    # Envelope
    "ProtocolEventEnvelope",
    # From Event Protocol
    "ProtocolFromEvent",
    # Registry
    "ProtocolEventBusRegistry",
    # Log Emitter
    "ProtocolEventBusLogEmitter",
]
