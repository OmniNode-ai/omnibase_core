"""
Protocol for event bus subscription operations (ISP - Interface Segregation Principle).

This module provides the ProtocolEventBusSubscriber protocol definition
for components that only need to subscribe to events, without requiring
the full ProtocolEventBus interface.

Design Principles:
- Minimal interface: Only subscription-related methods
- Runtime checkable: Supports duck typing with @runtime_checkable
- ISP compliant: Components that only subscribe don't need publish/lifecycle methods

.. versionchanged:: 0.14.0
    Updated subscribe() signature to use node_identity instead of group_id,
    and added purpose parameter for consumer group classification.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal, Protocol, runtime_checkable

from omnibase_core.protocols.event_bus.protocol_event_message import (
    ProtocolEventMessage,
)
from omnibase_core.protocols.event_bus.protocol_node_identity import (
    ProtocolNodeIdentity,
)

# Type alias for consumer group purpose classification
ConsumerGroupPurpose = Literal[
    "consume",
    "introspection",
    "replay",
    "audit",
    "backfill",
    "contract-registry",
]


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
        >>> from omnibase_infra.models import ModelNodeIdentity
        >>>
        >>> class MyConsumer:
        ...     def __init__(self, subscriber: ProtocolEventBusSubscriber):
        ...         self.subscriber = subscriber
        ...
        ...     async def start_listening(self) -> None:
        ...         identity = ModelNodeIdentity(
        ...             env="dev",
        ...             service="my-service",
        ...             node_name="consumer",
        ...             version="v1",
        ...         )
        ...         async def handler(msg: ProtocolEventMessage) -> None:
        ...             print(f"Received: {msg}")
        ...         self.unsubscribe = await self.subscriber.subscribe(
        ...             "my.topic",
        ...             identity,
        ...             handler,
        ...         )
        ...
        ...     async def stop_listening(self) -> None:
        ...         await self.unsubscribe()

    .. versionchanged:: 0.14.0
        Updated subscribe() to use node_identity instead of group_id.
    """

    async def subscribe(
        self,
        topic: str,
        node_identity: ProtocolNodeIdentity,
        on_message: Callable[[ProtocolEventMessage], Awaitable[None]],
        *,
        purpose: ConsumerGroupPurpose = "consume",
    ) -> Callable[[], Awaitable[None]]:
        """
        Subscribe to a topic with a message handler.

        Creates a subscription to the specified topic. Messages are delivered
        to the on_message callback. Returns an unsubscribe function that can
        be called to stop receiving messages.

        The consumer group ID is derived from the node identity using the
        canonical format: ``{env}.{service}.{node_name}.{purpose}.{version}``.

        Args:
            topic: The topic to subscribe to.
            node_identity: Node identity used to derive the consumer group ID.
                Contains env, service, node_name, and version components.
            on_message: Async callback invoked for each received message.
            purpose: Consumer group purpose classification. Defaults to "consume".
                Used in the consumer group ID derivation for disambiguation.
                Valid values: "consume", "introspection", "replay", "audit",
                "backfill", "contract-registry".

        Returns:
            An async function that, when called, unsubscribes from the topic.

        Raises:
            OnexError: If subscription fails (connection error, invalid topic, etc.).

        Example:
            >>> identity = ModelNodeIdentity(
            ...     env="dev",
            ...     service="my-service",
            ...     node_name="handler",
            ...     version="v1",
            ... )
            >>> unsubscribe = await bus.subscribe(
            ...     "events.user.created",
            ...     identity,
            ...     handle_user_created,
            ... )
            >>> # Consumer group: "dev.my-service.handler.consume.v1"
            >>> # Later, to stop receiving messages:
            >>> await unsubscribe()

        .. versionchanged:: 0.14.0
            Replaced group_id parameter with node_identity and added purpose.
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


__all__ = ["ProtocolEventBusSubscriber", "ConsumerGroupPurpose"]
