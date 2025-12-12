"""
Pydantic model for node discovery results.

Defines the structured result model for node discovery operations
within the ONEX architecture.
"""

from typing import Any

from pydantic import Field

from omnibase_core.models.core.model_base_result import ModelBaseResult
from omnibase_core.models.core.model_node_info import ModelNodeInfo


class ModelNodeDiscoveryResult(ModelBaseResult):
    """
    Structured result model for node discovery operations.

    Contains the results of discovering ONEX nodes through various
    discovery mechanisms (registry, filesystem, etc.).
    """

    nodes: list[ModelNodeInfo] = Field(
        default_factory=list,
        description="List of discovered nodes",
    )
    source: str = Field(
        default=...,
        description="Discovery source (registry, filesystem, etc.)",
    )
    total_available: int | None = Field(
        default=None,
        description="Total nodes available in source",
    )
    discovery_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional discovery metadata",
    )
    execution_time_ms: float | None = Field(
        default=None,
        description="Discovery execution time in milliseconds",
    )


# Compatibility - export both classes
__all__ = ["ModelNodeDiscoveryResult", "ModelNodeInfo"]
