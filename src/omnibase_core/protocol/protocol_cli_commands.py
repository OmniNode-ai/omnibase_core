"""
Protocol for CLI commands tool (shared).
Defines the interface for CLI command operations and orchestration.
"""

from typing import Protocol

from omnibase_core.nodes.node_kafka_event_bus.v1_0_0.models.model_cli_command import (
    ModelCliCommand,
)
from omnibase_core.nodes.node_kafka_event_bus.v1_0_0.models.state import (
    KafkaEventBusOutputState,
)


class ProtocolCliCommands(Protocol):
    """
    Protocol for CLI commands tool (shared).
    Implementations should provide methods for running, parsing, and managing CLI commands.
    """

    def run_command(self, command: ModelCliCommand) -> KafkaEventBusOutputState:
        """
        Run a CLI command with the given arguments.
        Args:
            command (ModelCliCommand): The command model to run.
        Returns:
            KafkaEventBusOutputState: The output model for the command.
        """
        ...
