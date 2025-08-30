"""
Model for Docker placement constraints configuration.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelDockerPlacementConstraints(BaseModel):
    """Docker placement constraints configuration."""

    constraints: List[str] = Field(
        default_factory=list,
        description="Placement constraints (e.g., 'node.role==worker')",
    )
    preferences: List[str] = Field(
        default_factory=list, description="Placement preferences"
    )
    max_replicas_per_node: Optional[int] = Field(
        default=None, description="Maximum replicas per node"
    )
