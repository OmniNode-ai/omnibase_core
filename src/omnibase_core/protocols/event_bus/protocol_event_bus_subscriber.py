"""
Protocol for event bus subscription operations (ISP - Interface Segregation Principle).

This module provides the ProtocolEventBusSubscriber protocol definition
for components that only need to subscribe to events, without requiring
the full ProtocolEventBus interface.

Design Principles:
- Minimal interface: Only subscription-related methods
- Runtime checkable: Supports duck typing with @runtime_checkable
- ISP compliant: Components that only subscribe don't need publish/lifecycle methods
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from omnibase_core.protocols.event_bus.protocol_event_message import (
    ProtocolEventMessage,
)


@runtime_checkable
class ProtocolEventBusSubscriber(Protocol):
    """
    Protocol for event bus subscription operations.

    This is a minimal interface for components that only need to consume events.
    It follows the Interface Segregation Principle (ISP) by separating
    subscription concerns from publishing and lifecycle management.

    Use Cases:
    - Nodes that consume events but don't produce them
    - Reducer nodes aggregating events from multiple sources
    - Services that only need to listen for specific event types

    Example:
        >>> class MyConsumer:
        ...     def __init__(self, subscriber: ProtocolEventBusSubscriber):
        ...         self.subscriber = subscriber
        ...
        ...     async def start_listening(self) -> None:
        ...         async def handler(msg: ProtocolEventMessage) -> None:
        ...             print(f"Received: {msg}")
        ...         self.unsubscribe = await self.subscriber.subscribe(
        ...             "my.topic",
        ...             "my-consumer-group",
        ...             handler,
        ...         )
        ...
        ...     async def stop_listening(self) -> None:
        ...         await self.unsubscribe()
    """

    async def subscribe(
        self,
        topic: str,
        group_id: str,
        on_message: Callable[[ProtocolEventMessage], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        """
        Subscribe to a topic with a message handler.

        Creates a subscription to the specified topic. Messages are delivered
        to the on_message callback. Returns an unsubscribe function that can
        be called to stop receiving messages.

        Args:
            topic: The topic to subscribe to.
            group_id: Consumer group ID for load balancing and offset management.
            on_message: Async callback invoked for each received message.

        Returns:
            An async function that, when called, unsubscribes from the topic.

        Raises:
            OnexError: If subscription fails (connection error, invalid topic, etc.).

        Example:
            >>> unsubscribe = await bus.subscribe(
            ...     "events.user.created",
            ...     "user-service",
            ...     handle_user_created,
            ... )
            >>> # Later, to stop receiving messages:
            >>> await unsubscribe()
        """
        ...

    async def start_consuming(self) -> None:
        """
        Start consuming messages from all subscribed topics.

        This method begins the message consumption loop. It should be called
        after all subscriptions have been set up. The method may run
        indefinitely or until shutdown is requested.

        Raises:
            OnexError: If consumption cannot be started.

        Note:
            Some implementations may start consuming automatically on subscribe.
            Check implementation documentation for specific behavior.
        """
        ...


__all__ = ["ProtocolEventBusSubscriber"]
