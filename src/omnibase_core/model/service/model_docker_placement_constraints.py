"""
Model for Docker placement constraints configuration.
"""

from pydantic import BaseModel, Field


class ModelDockerPlacementConstraints(BaseModel):
    """Docker placement constraints configuration."""

    constraints: list[str] = Field(
        default_factory=list,
        description="Placement constraints (e.g., 'node.role==worker')",
    )
    preferences: list[str] = Field(
        default_factory=list,
        description="Placement preferences",
    )
    max_replicas_per_node: int | None = Field(
        default=None,
        description="Maximum replicas per node",
    )
