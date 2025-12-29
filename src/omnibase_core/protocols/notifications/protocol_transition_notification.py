"""
Protocols for state transition notification publishing and consuming.

This module defines the protocol contracts for publishing and consuming
state transition notifications in the ONEX framework.

Design Rationale:
    State transition notifications follow the Observer pattern, enabling
    loose coupling between reducers (state machines) and orchestrators
    (workflow coordinators). These protocols establish the contracts for:

    1. Publishers: Emit notifications after state transitions are committed
    2. Consumers: Subscribe to notifications for specific aggregate types

    The separation into publisher and consumer protocols follows the
    Interface Segregation Principle (ISP), allowing components to depend
    only on the capabilities they need.

Patterns:
    - Observer Pattern: Orchestrators observe state transitions
    - Event-Driven Architecture: Async notification delivery
    - Protocol-based DI: Duck typing support via @runtime_checkable

Usage - Publisher:
    >>> from omnibase_core.protocols.notifications import (
    ...     ProtocolTransitionNotificationPublisher,
    ... )
    >>>
    >>> class KafkaNotificationPublisher:
    ...     '''Kafka-based notification publisher.'''
    ...
    ...     async def publish(
    ...         self, notification: ModelStateTransitionNotification
    ...     ) -> None:
    ...         await self.kafka_producer.send(
    ...             topic=f"notifications.{notification.aggregate_type}",
    ...             value=notification.model_dump_json().encode(),
    ...         )
    ...
    ...     async def publish_batch(
    ...         self, notifications: list[ModelStateTransitionNotification]
    ...     ) -> None:
    ...         for notification in notifications:
    ...             await self.publish(notification)

Usage - Consumer:
    >>> from omnibase_core.protocols.notifications import (
    ...     ProtocolTransitionNotificationConsumer,
    ... )
    >>>
    >>> class OrchestratorNotificationHandler:
    ...     '''Orchestrator that reacts to state transitions.'''
    ...
    ...     def __init__(
    ...         self, consumer: ProtocolTransitionNotificationConsumer
    ...     ) -> None:
    ...         self.consumer = consumer
    ...
    ...     async def start(self) -> None:
    ...         await self.consumer.subscribe(
    ...             "registration",
    ...             self.handle_registration_transition,
    ...         )
    ...
    ...     async def handle_registration_transition(
    ...         self, notification: ModelStateTransitionNotification
    ...     ) -> None:
    ...         if notification.to_state == "active":
    ...             # Trigger downstream workflow
    ...             await self.start_onboarding_workflow(notification)

Thread Safety:
    Protocol implementations should be thread-safe if used in concurrent
    contexts. Publishers typically use connection pooling, and consumers
    should handle concurrent message delivery appropriately.

See Also:
    omnibase_core.models.notifications.ModelStateTransitionNotification:
        The notification model published/consumed by these protocols.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.notifications.model_state_transition_notification import (
        ModelStateTransitionNotification,
    )


@runtime_checkable
class ProtocolTransitionNotificationPublisher(Protocol):
    """
    Protocol for publishing state transition notifications.

    Implementations are responsible for delivering notifications to consumers
    after state transitions are committed. This protocol supports both
    single-notification and batch publishing.

    This protocol is @runtime_checkable, enabling isinstance() checks for
    duck typing validation at runtime.

    Methods:
        publish: Publish a single notification.
        publish_batch: Publish multiple notifications atomically or in sequence.

    Design Notes:
        - publish() is for real-time notification delivery
        - publish_batch() is for efficiency when multiple transitions occur
        - Implementations should handle delivery failures gracefully
        - Idempotency should be handled via projection_version

    Example:
        >>> class MyPublisher:
        ...     async def publish(
        ...         self, notification: ModelStateTransitionNotification
        ...     ) -> None:
        ...         # Send to message bus
        ...         await self.message_bus.send(notification)
        ...
        ...     async def publish_batch(
        ...         self, notifications: list[ModelStateTransitionNotification]
        ...     ) -> None:
        ...         # Send batch to message bus
        ...         await self.message_bus.send_batch(notifications)
        >>>
        >>> publisher = MyPublisher()
        >>> isinstance(publisher, ProtocolTransitionNotificationPublisher)  # True
    """

    async def publish(
        self,
        notification: ModelStateTransitionNotification,
    ) -> None:
        """
        Publish a single state transition notification.

        This method should be called after a state transition is committed
        to notify orchestrators of the change.

        Args:
            notification: The state transition notification to publish.

        Raises:
            OnexError: If publishing fails (connection error, serialization, etc.).

        Note:
            Implementations should ensure at-least-once delivery semantics.
            Consumers should be prepared to handle duplicate notifications
            using the projection_version for deduplication.

        Example:
            >>> notification = ModelStateTransitionNotification(
            ...     aggregate_type="registration",
            ...     aggregate_id=uuid4(),
            ...     from_state="pending",
            ...     to_state="active",
            ...     projection_version=1,
            ...     correlation_id=uuid4(),
            ...     causation_id=uuid4(),
            ...     timestamp=datetime.now(UTC),
            ... )
            >>> await publisher.publish(notification)
        """
        ...

    async def publish_batch(
        self,
        notifications: list[ModelStateTransitionNotification],
    ) -> None:
        """
        Publish multiple state transition notifications.

        This method is provided for efficiency when multiple transitions
        occur in a single unit of work. Implementations may:
        - Publish atomically (all-or-nothing)
        - Publish sequentially with ordering guarantees
        - Publish in parallel for performance

        Args:
            notifications: List of notifications to publish.

        Raises:
            OnexError: If publishing fails.

        Note:
            The order of notifications in the list should be preserved
            when delivery order matters for workflow correctness.

        Example:
            >>> notifications = [notification1, notification2, notification3]
            >>> await publisher.publish_batch(notifications)
        """
        ...


@runtime_checkable
class ProtocolTransitionNotificationConsumer(Protocol):
    """
    Protocol for consuming state transition notifications.

    Implementations enable orchestrators to subscribe to state transitions
    for specific aggregate types and react to changes.

    This protocol is @runtime_checkable, enabling isinstance() checks for
    duck typing validation at runtime.

    Methods:
        subscribe: Register a handler for notifications of a specific aggregate type.

    Design Notes:
        - Handlers are async to support non-blocking processing
        - aggregate_type filtering enables targeted subscriptions
        - Handlers receive the full notification for decision-making
        - Multiple handlers can subscribe to the same aggregate type

    Example:
        >>> class MyConsumer:
        ...     def __init__(self) -> None:
        ...         self.handlers: dict[str, list] = {}
        ...
        ...     async def subscribe(
        ...         self,
        ...         aggregate_type: str,
        ...         handler: Callable[
        ...             [ModelStateTransitionNotification], Awaitable[None]
        ...         ],
        ...     ) -> None:
        ...         if aggregate_type not in self.handlers:
        ...             self.handlers[aggregate_type] = []
        ...         self.handlers[aggregate_type].append(handler)
        >>>
        >>> consumer = MyConsumer()
        >>> isinstance(consumer, ProtocolTransitionNotificationConsumer)  # True
    """

    async def subscribe(
        self,
        aggregate_type: str,
        handler: Callable[[ModelStateTransitionNotification], Awaitable[None]],
    ) -> None:
        """
        Subscribe to notifications for a specific aggregate type.

        Registers a handler to be called when notifications are received
        for the specified aggregate type. Multiple handlers can be
        registered for the same aggregate type.

        Args:
            aggregate_type: The type of aggregate to subscribe to
                (e.g., "registration", "intelligence").
            handler: Async callback invoked for each notification.
                The handler receives the full ModelStateTransitionNotification
                and should process it without blocking.

        Raises:
            OnexError: If subscription fails (connection error, invalid type, etc.).

        Note:
            Handlers should be idempotent and handle potential duplicate
            notifications gracefully. Use projection_version for deduplication.

        Example:
            >>> async def handle_registration(
            ...     notification: ModelStateTransitionNotification,
            ... ) -> None:
            ...     if notification.to_state == "active":
            ...         await trigger_onboarding(notification.aggregate_id)
            ...
            >>> await consumer.subscribe("registration", handle_registration)
        """
        ...


__all__ = [
    "ProtocolTransitionNotificationPublisher",
    "ProtocolTransitionNotificationConsumer",
]
