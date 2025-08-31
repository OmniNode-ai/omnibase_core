from typing import Protocol

from omnibase_core.model.service.model_event_bus_bootstrap_result import (
    ModelEventBusBootstrapResult,
)
from omnibase_core.nodes.node_kafka_event_bus.v1_0_0.tools.tool_kafka_event_bus import (
    ModelModelEventBusConfig,
)


class ProtocolToolBootstrap(Protocol):
    """
    Protocol for bootstrap tool for the Kafka event bus node.
    Accepts a strongly-typed ModelModelEventBusConfig and returns a ModelEventBusBootstrapResult.
    """

    def bootstrap_kafka_cluster(
        self,
        config: ModelModelEventBusConfig,
    ) -> ModelEventBusBootstrapResult:
        """
        Perform bootstrap initialization for the Kafka cluster.
        Args:
            config: ModelModelEventBusConfig
        Returns:
            ModelEventBusBootstrapResult
        """
        ...
