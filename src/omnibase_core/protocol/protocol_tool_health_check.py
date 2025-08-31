from typing import Protocol

from omnibase_core.nodes.node_kafka_event_bus.v1_0_0.tools.tool_kafka_event_bus import (
    KafkaHealthCheckResult,
    ModelModelEventBusConfig,
)


class ProtocolToolHealthCheck(Protocol):
    """
    Protocol for health check tool for the Kafka event bus node.
    Accepts a strongly-typed ModelModelEventBusConfig and returns a KafkaHealthCheckResult.
    """

    def health_check(self, config: ModelModelEventBusConfig) -> KafkaHealthCheckResult:
        """
        Perform a health check on the Kafka event bus backend.
        Args:
            config: ModelModelEventBusConfig
        Returns:
            KafkaHealthCheckResult: The result of the health check
        """
        ...
