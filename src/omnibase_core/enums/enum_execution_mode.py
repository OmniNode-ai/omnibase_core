# DEPRECATED: Use ModelExecutionMode in model_execution_mode.py
# This file is retained for backward compatibility only.

"""
Execution Mode Enum

Execution modes for CLI commands and node operations.
"""

from enum import Enum


class EnumExecutionMode(Enum):
    """
    Execution modes for CLI commands and node operations.

    Defines how commands are executed and routed through the ONEX system.
    """

    DIRECT = "direct"
    INMEMORY = "inmemory"
    KAFKA = "kafka"

    def __str__(self) -> str:
        """Return the string value of the execution mode."""
        return self.value

    def is_synchronous(self) -> bool:
        """Check if this execution mode is synchronous."""
        return self == self.DIRECT

    def is_asynchronous(self) -> bool:
        """Check if this execution mode is asynchronous."""
        return self in [self.INMEMORY, self.KAFKA]

    def is_distributed(self) -> bool:
        """Check if this execution mode is distributed."""
        return self == self.KAFKA

    def is_local(self) -> bool:
        """Check if this execution mode is local."""
        return self in [self.DIRECT, self.INMEMORY]

    def requires_event_bus(self) -> bool:
        """Check if this mode requires an event bus."""
        return self in [self.INMEMORY, self.KAFKA]

    def supports_scaling(self) -> bool:
        """Check if this mode supports horizontal scaling."""
        return self == self.KAFKA

    def get_typical_latency_ms(self) -> int:
        """Get typical latency for this execution mode."""
        latency_map = {
            self.DIRECT: 5,  # Very low latency
            self.INMEMORY: 20,  # Low latency with async overhead
            self.KAFKA: 100,  # Higher latency due to network/serialization
        }
        return latency_map[self]

    def get_reliability_level(self) -> str:
        """Get reliability level for this execution mode."""
        reliability_map = {
            self.DIRECT: "low",  # No persistence, single point of failure
            self.INMEMORY: "medium",  # Local persistence, single process
            self.KAFKA: "high",  # Distributed persistence, fault tolerance
        }
        return reliability_map[self]
