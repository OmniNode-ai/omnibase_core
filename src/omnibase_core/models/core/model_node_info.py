"""
Pydantic model for node information.

Information about a discovered ONEX node, used in node discovery results.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelNodeInfo(BaseModel):
    """Information about a discovered ONEX node."""

    name: str = Field(default=..., description="Node name")
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Node version",
    )
    description: str = Field(default=..., description="Node description")
    status: str = Field(default=..., description="Node status")
    trust_level: str = Field(default=..., description="Node trust level")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Node capabilities",
    )
    namespace: str = Field(default=..., description="Node namespace")
