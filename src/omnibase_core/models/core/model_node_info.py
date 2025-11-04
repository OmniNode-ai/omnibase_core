from typing import Any

from pydantic import Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

"""
Pydantic model for node information.

Information about a discovered ONEX node, used in node discovery results.
"""

from pydantic import BaseModel


class ModelNodeInfo(BaseModel):
    """Information about a discovered ONEX node."""

    name: str = Field(default=..., description="Node name")
    version: ModelSemVer = Field(default=..., description="Node version")
    description: str = Field(default=..., description="Node description")
    status: str = Field(default=..., description="Node status")
    trust_level: str = Field(default=..., description="Node trust level")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Node capabilities",
    )
    namespace: str = Field(default=..., description="Node namespace")
