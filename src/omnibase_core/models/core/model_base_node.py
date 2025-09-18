"""
Base Node Class - ONEX Four-Node Architecture

Base class for all ONEX nodes (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR).
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_semver import SemVerField


class ModelNodeInfo(BaseModel):
    """Node metadata information model."""

    type: str = Field(..., description="Node type")
    name: str = Field(..., description="Node name")
    version: SemVerField = Field(..., description="Node version")


class ModelBaseNode(BaseModel, ABC):
    """
    Abstract base class for all ONEX nodes.

    All nodes must extend this class and implement the execute method.
    """

    node_type: str = Field(..., description="Type of the node")
    node_name: str = Field(..., description="Name of the node")
    version: SemVerField = Field(..., description="Node version")

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

    def get_node_info(self) -> ModelNodeInfo:
        """Get node metadata information."""
        return ModelNodeInfo(
            type=self.node_type, name=self.node_name, version=self.version
        )
