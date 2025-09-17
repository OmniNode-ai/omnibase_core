"""
Base Node Class - ONEX Four-Node Architecture

Base class for all ONEX nodes (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR).
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseNode(ABC):
    """
    Abstract base class for all ONEX nodes.

    All nodes must extend this class and implement the execute method.
    """

    def __init__(self) -> None:
        self.node_type: str = ""
        self.node_name: str = ""
        self.version: str = ""

    @abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the node's primary function.

        Args:
            input_data: Input data for node processing

        Returns:
            Processed output data
        """
        pass

    def get_node_info(self) -> dict[str, str]:
        """Get node metadata information."""
        return {"type": self.node_type, "name": self.node_name, "version": self.version}
