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
from omnibase_core.protocols.event_bus.protocol_event_bus_log_emitter import (
    ProtocolEventBusLogEmitter,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_registry import (
    ProtocolEventBusRegistry,
)
from omnibase_core.protocols.event_bus.protocol_event_envelope import (
    ProtocolEventEnvelope,
)
from omnibase_core.protocols.event_bus.protocol_event_message import (
    ProtocolEventMessage,
)
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
    # Event Bus
    "ProtocolEventBus",
    "ProtocolEventBusBase",
    "ProtocolSyncEventBus",
    "ProtocolAsyncEventBus",
    # Envelope
    "ProtocolEventEnvelope",
    # Registry
    "ProtocolEventBusRegistry",
    # Log Emitter
    "ProtocolEventBusLogEmitter",
]
