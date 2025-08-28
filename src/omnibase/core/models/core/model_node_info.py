"""
Pydantic model for node information.

Information about a discovered ONEX node, used in node discovery results.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelNodeInfo(BaseModel):
    """Information about a discovered ONEX node."""

    name: str = Field(..., description="Node name")
    version: str = Field(..., description="Node version")
    description: str = Field(..., description="Node description")
    status: str = Field(..., description="Node status")
    trust_level: str = Field(..., description="Node trust level")
    capabilities: List[str] = Field(
        default_factory=list, description="Node capabilities"
    )
    namespace: str = Field(..., description="Node namespace")
