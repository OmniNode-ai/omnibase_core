"""
Notification protocols for the ONEX framework.

This module provides protocol definitions for notification publishing
and consuming in the ONEX framework.

Protocols enable:
- Duck typing for notification services
- Interface segregation (separate publish/consume concerns)
- Runtime type checking via @runtime_checkable
- Flexible implementation strategies (Kafka, in-memory, etc.)

Protocols:
    ProtocolTransitionNotificationPublisher: Contract for publishing
        state transition notifications.
    ProtocolTransitionNotificationConsumer: Contract for consuming
        state transition notifications.

Usage:
    >>> from omnibase_core.protocols.notifications import (
    ...     ProtocolTransitionNotificationPublisher,
    ...     ProtocolTransitionNotificationConsumer,
    ... )
    >>>
    >>> class MyPublisher:
    ...     async def publish(
    ...         self, notification: ModelStateTransitionNotification
    ...     ) -> None:
    ...         # Implementation
    ...         pass
    ...
    ...     async def publish_batch(
    ...         self, notifications: list[ModelStateTransitionNotification]
    ...     ) -> None:
    ...         # Implementation
    ...         pass
    >>>
    >>> publisher = MyPublisher()
    >>> isinstance(publisher, ProtocolTransitionNotificationPublisher)  # True

See Also:
    omnibase_core.models.notifications: Notification models that these
        protocols work with.
"""

from omnibase_core.protocols.notifications.protocol_transition_notification import (
    ProtocolTransitionNotificationConsumer,
    ProtocolTransitionNotificationPublisher,
)

__all__ = [
    "ProtocolTransitionNotificationPublisher",
    "ProtocolTransitionNotificationConsumer",
]
