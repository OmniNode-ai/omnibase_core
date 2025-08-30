"""
Pydantic model for node discovery results.

Defines the structured result model for node discovery operations
within the ONEX architecture.
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from omnibase_core.model.core.model_base_result import ModelBaseResult
from omnibase_core.model.core.model_node_info import ModelNodeInfo


class ModelNodeDiscoveryResult(ModelBaseResult):
    """
    Structured result model for node discovery operations.

    Contains the results of discovering ONEX nodes through various
    discovery mechanisms (registry, filesystem, etc.).
    """

    nodes: List[ModelNodeInfo] = Field(
        default_factory=list, description="List of discovered nodes"
    )
    source: str = Field(
        ..., description="Discovery source (registry, filesystem, etc.)"
    )
    total_available: Optional[int] = Field(
        None, description="Total nodes available in source"
    )
    discovery_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional discovery metadata"
    )
    execution_time_ms: Optional[float] = Field(
        None, description="Discovery execution time in milliseconds"
    )


# Backward compatibility - export both classes
__all__ = ["ModelNodeInfo", "ModelNodeDiscoveryResult"]
