"""
Protocol for Kafka Event Bus Implementation.

Defines the interface for Kafka-based event bus implementations.
"""

from typing import Protocol, runtime_checkable

from omnibase_core.protocol.protocol_event_bus_types import ProtocolEventBus


@runtime_checkable
class ProtocolEventBusKafka(ProtocolEventBus, Protocol):
    """Protocol for Kafka event bus implementations."""

    def get_kafka_config(self) -> dict:
        """Get Kafka-specific configuration."""
        ...

    def get_consumer_group_id(self) -> str:
        """Get the consumer group ID for this Kafka consumer."""
        ...

    def get_bootstrap_servers(self) -> list:
        """Get the list of Kafka bootstrap servers."""
        ...
