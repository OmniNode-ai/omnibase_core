from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_semver import ModelSemVer
from omnibase_core.models.discovery.model_node_introspection_event import (
    ModelNodeCapabilities,
)


class MixinNodeIntrospectionData(BaseModel):
    """
    Strongly typed container for node introspection data.

    This replaces the loose Dict[str, str | ModelSemVer | List[str] | ...] with
    proper type safety and clear field definitions. Uses the canonical
    ModelNodeCapabilities structure for capabilities data.
    """

    node_name: str = Field(..., description="Node name identifier")
    version: ModelSemVer = Field(..., description="Semantic version of the node")
    capabilities: ModelNodeCapabilities = Field(..., description="Node capabilities")
    tags: list[str] = Field(default_factory=list, description="Discovery tags")
    health_endpoint: str | None = Field(None, description="Health check endpoint")
