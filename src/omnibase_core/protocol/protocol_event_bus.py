# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.128231'
# description: Stamped by ToolPython
# entrypoint: python://protocol_event_bus
# hash: d08b73065d9e8de6ac3b18881f8669d08f07ca6678ec78d1f0cdb96e3b9016eb
# last_modified_at: '2025-05-29T14:14:00.220362+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_event_bus.py
# namespace: python://omnibase.protocol.protocol_event_bus
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 2d9c79c5-6422-462b-b10c-e080a10c1d42
# version: 1.0.0
# === /OmniNode:Metadata ===


from collections.abc import Callable
from typing import Protocol, runtime_checkable

from omnibase_core.models.core.model_onex_event import OnexEvent
from omnibase_core.protocol.protocol_event_bus_types import EventBusCredentialsModel


@runtime_checkable
class ProtocolEventBus(Protocol):
    """
    Canonical protocol for ONEX event bus (runtime/ placement).
    Defines publish/subscribe interface for event emission and handling.
    All event bus implementations must conform to this interface.
    Supports both synchronous and asynchronous methods for maximum flexibility.
    Implementations may provide either or both, as appropriate.
    Optionally supports clear() for test/lifecycle management.

    # ROADMAP: Future protocol extensions for production scalability
    #
    # Phase 1 - Backend Abstraction:
    # - Pluggable backend interface (Redis, RabbitMQ, NATS)
    # - Backend selection via configuration
    # - Fallback mechanisms for backend failures
    #
    # Phase 2 - Persistence & Reliability:
    # - Message persistence for durability
    # - Dead letter queues for failed messages
    # - Message replay capabilities
    # - Delivery acknowledgements
    #
    # Phase 3 - Security & Multi-tenancy:
    # - Authentication and authorization
    # - Multi-tenant isolation
    # - Message encryption in transit
    # - Audit logging for compliance
    #
    # Phase 4 - Advanced Features:
    # - Message routing and filtering
    # - Priority queues
    # - Rate limiting per tenant
    # - Monitoring and health checks
    """

    def __init__(
        self,
        credentials: EventBusCredentialsModel | None = None,
        **kwargs,
    ): ...

    def publish(self, event: OnexEvent) -> None:
        """
        Publish an event to the bus (synchronous).
        Args:
            event: OnexEvent to emit
        """
        ...

    async def publish_async(self, event: OnexEvent) -> None:
        """
        Publish an event to the bus (asynchronous).
        Args:
            event: OnexEvent to emit
        """
        ...

    def subscribe(self, callback: Callable[[OnexEvent], None]) -> None:
        """
        Subscribe a callback to receive events (synchronous).
        Args:
            callback: Callable invoked with each OnexEvent
        """
        ...

    async def subscribe_async(self, callback: Callable[[OnexEvent], None]) -> None:
        """
        Subscribe a callback to receive events (asynchronous).
        Args:
            callback: Callable invoked with each OnexEvent
        """
        ...

    def unsubscribe(self, callback: Callable[[OnexEvent], None]) -> None:
        """
        Unsubscribe a previously registered callback (synchronous).
        Args:
            callback: Callable to remove
        """
        ...

    async def unsubscribe_async(self, callback: Callable[[OnexEvent], None]) -> None:
        """
        Unsubscribe a previously registered callback (asynchronous).
        Args:
            callback: Callable to remove
        """
        ...

    def clear(self) -> None:
        """
        Remove all subscribers from the event bus. Optional, for test/lifecycle management.
        """
        ...
