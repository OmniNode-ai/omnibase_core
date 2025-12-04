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

from typing import (
    TYPE_CHECKING,
    Awaitable,
    Callable,
    Generic,
    Literal,
    Protocol,
    TypeVar,
    runtime_checkable,
)
from uuid import UUID

from omnibase_core.protocols.base import (
    ContextValue,
    LiteralEventPriority,
    LiteralLogLevel,
    ProtocolDateTime,
    ProtocolSemVer,
    T_co,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# Type Variables
# =============================================================================

T = TypeVar("T")


# =============================================================================
# Event Message Protocol
# =============================================================================


@runtime_checkable
class ProtocolEventMessage(Protocol):
    """
    Protocol for event message objects in the event bus.

    Represents a message that can be published to and received from
    the event bus, with acknowledgment support.
    """

    @property
    def topic(self) -> str:
        """Get the topic this message was published to."""
        ...

    @property
    def key(self) -> bytes | None:
        """Get the message key."""
        ...

    @property
    def value(self) -> bytes:
        """Get the message value."""
        ...

    @property
    def headers(self) -> dict[str, str]:
        """Get the message headers."""
        ...

    async def ack(self) -> None:
        """Acknowledge the message."""
        ...

    async def nack(self) -> None:
        """Negatively acknowledge the message."""
        ...


# =============================================================================
# Event Bus Headers Protocol
# =============================================================================


@runtime_checkable
class ProtocolEventBusHeaders(Protocol):
    """
    Protocol for standardized headers for ONEX event bus messages.

    Enforces strict interoperability across all agents and prevents
    integration failures from header naming inconsistencies.
    """

    @property
    def content_type(self) -> str:
        """Get content type (e.g., 'application/json')."""
        ...

    @property
    def correlation_id(self) -> UUID:
        """Get correlation ID for distributed tracing."""
        ...

    @property
    def message_id(self) -> UUID:
        """Get unique message ID."""
        ...

    @property
    def timestamp(self) -> ProtocolDateTime:
        """Get message timestamp."""
        ...

    @property
    def source(self) -> str:
        """Get message source identifier."""
        ...

    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        ...

    @property
    def schema_version(self) -> ProtocolSemVer:
        """Get schema version."""
        ...

    @property
    def destination(self) -> str | None:
        """Get optional destination."""
        ...

    @property
    def trace_id(self) -> str | None:
        """Get OpenTelemetry trace ID."""
        ...

    @property
    def span_id(self) -> str | None:
        """Get OpenTelemetry span ID."""
        ...

    @property
    def parent_span_id(self) -> str | None:
        """Get parent span ID for trace context."""
        ...

    @property
    def operation_name(self) -> str | None:
        """Get operation name."""
        ...

    @property
    def priority(self) -> LiteralEventPriority | None:
        """Get message priority."""
        ...

    @property
    def routing_key(self) -> str | None:
        """Get routing key."""
        ...

    @property
    def partition_key(self) -> str | None:
        """Get partition key."""
        ...

    @property
    def retry_count(self) -> int | None:
        """Get retry count."""
        ...

    @property
    def max_retries(self) -> int | None:
        """Get max retries."""
        ...

    @property
    def ttl_seconds(self) -> int | None:
        """Get time-to-live in seconds."""
        ...


# =============================================================================
# Kafka Event Bus Adapter Protocol
# =============================================================================


@runtime_checkable
class ProtocolKafkaEventBusAdapter(Protocol):
    """
    Protocol for Event Bus Adapters supporting pluggable Kafka/Redpanda backends.

    Implements the ONEX Messaging Design enabling drop-in support for
    both Kafka and Redpanda without code changes.
    """

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: ProtocolEventBusHeaders,
    ) -> None:
        """Publish a message to a topic."""
        ...

    async def subscribe(
        self,
        topic: str,
        group_id: str,
        on_message: Callable[[ProtocolEventMessage], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        """
        Subscribe to a topic.

        Returns an unsubscribe function.
        """
        ...

    async def close(self) -> None:
        """Close the adapter connection."""
        ...


# =============================================================================
# Event Bus Protocol
# =============================================================================


@runtime_checkable
class ProtocolEventBus(Protocol):
    """
    ONEX event bus protocol for distributed messaging infrastructure.

    Implements the ONEX Messaging Design with environment isolation
    and node group mini-meshes.
    """

    @property
    def adapter(self) -> ProtocolKafkaEventBusAdapter:
        """Get the underlying adapter."""
        ...

    @property
    def environment(self) -> str:
        """Get the environment (dev, staging, prod)."""
        ...

    @property
    def group(self) -> str:
        """Get the node group."""
        ...

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: ProtocolEventBusHeaders | None = None,
    ) -> None:
        """Publish a message to a topic."""
        ...

    async def subscribe(
        self,
        topic: str,
        group_id: str,
        on_message: Callable[[ProtocolEventMessage], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        """Subscribe to a topic."""
        ...

    async def broadcast_to_environment(
        self,
        command: str,
        payload: dict[str, ContextValue],
        target_environment: str | None = None,
    ) -> None:
        """Broadcast a command to all nodes in an environment."""
        ...

    async def send_to_group(
        self, command: str, payload: dict[str, ContextValue], target_group: str
    ) -> None:
        """Send a command to a specific node group."""
        ...

    async def close(self) -> None:
        """Close the event bus."""
        ...


# =============================================================================
# Event Envelope Protocol
# =============================================================================


@runtime_checkable
class ProtocolEventEnvelope(Protocol, Generic[T_co]):
    """
    Protocol defining the minimal interface for event envelopes.

    This protocol allows mixins to type-hint envelope parameters without
    importing the concrete ModelEventEnvelope class, breaking circular dependencies.
    """

    async def get_payload(self) -> T_co:
        """Get the wrapped event payload."""
        ...


# =============================================================================
# Event Bus Base Protocol
# =============================================================================


@runtime_checkable
class ProtocolEventBusBase(Protocol):
    """
    Base protocol for event bus operations.

    Defines common event publishing interface that both synchronous
    and asynchronous event buses must implement.
    """

    async def publish(self, event: ProtocolEventMessage) -> None:
        """Publish an event."""
        ...


# =============================================================================
# Sync Event Bus Protocol
# =============================================================================


@runtime_checkable
class ProtocolSyncEventBus(Protocol):
    """
    Protocol for synchronous event bus operations.

    Defines synchronous event publishing interface for event bus
    implementations that operate synchronously.
    """

    async def publish(self, event: ProtocolEventMessage) -> None:
        """Publish an event asynchronously."""
        ...

    async def publish_sync(self, event: ProtocolEventMessage) -> None:
        """Publish an event synchronously."""
        ...


# =============================================================================
# Async Event Bus Protocol
# =============================================================================


@runtime_checkable
class ProtocolAsyncEventBus(Protocol):
    """
    Protocol for asynchronous event bus operations.

    Defines asynchronous event publishing interface for event bus
    implementations that operate asynchronously.
    """

    async def publish(self, event: ProtocolEventMessage) -> None:
        """Publish an event."""
        ...

    async def publish_async(self, event: ProtocolEventMessage) -> None:
        """Publish an event asynchronously."""
        ...


# =============================================================================
# Event Bus Registry Protocol
# =============================================================================


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


# =============================================================================
# Event Bus Log Emitter Protocol
# =============================================================================


@runtime_checkable
class ProtocolEventBusLogEmitter(Protocol):
    """
    Protocol for structured log emission via event bus.

    Defines interface for components that can emit structured
    log events with typed data and log levels.
    """

    def emit_log_event(
        self,
        level: LiteralLogLevel,
        message: str,
        data: dict[str, str | int | float | bool],
    ) -> None:
        """Emit a structured log event."""
        ...


# =============================================================================
# Exports
# =============================================================================

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
