"""
Protocol for Kafka client used by intent publisher.

This module provides the ProtocolKafkaClient protocol definition
for simple string-based Kafka publishing used by MixinIntentPublisher.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolKafkaClient(Protocol):
    """Protocol for Kafka client used by intent publisher."""

    async def publish(self, topic: str, key: str, value: str) -> None:
        """Publish a message to a Kafka topic."""
        ...


__all__ = ["ProtocolKafkaClient"]
