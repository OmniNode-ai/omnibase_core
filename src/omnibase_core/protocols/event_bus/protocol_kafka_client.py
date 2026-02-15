"""
Protocol for Kafka client used by intent publisher.

This module provides the ProtocolKafkaClient protocol definition
for simple string-based Kafka publishing used by MixinIntentPublisher.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolKafkaClient(Protocol):
    """Minimal, publish-only Kafka client protocol used by intent publisher.

    This protocol is intentionally limited to a single ``publish`` method.
    Consuming, subscribing, and administrative operations are handled by
    separate, dedicated protocols. Keeping the surface area small allows
    nodes to depend only on the capability they actually need (publishing
    intents) without pulling in a full-featured Kafka client abstraction.
    """

    async def publish(self, topic: str, key: str, value: str) -> None:
        """Publish a message to a Kafka topic."""
        ...


__all__ = ["ProtocolKafkaClient"]
