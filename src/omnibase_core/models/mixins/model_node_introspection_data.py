from pydantic import BaseModel, Field

from omnibase_core.models.discovery.model_node_introspection_event import (
    ModelNodeCapabilities,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelNodeIntrospectionData(BaseModel):
    """
    Strongly typed container for node introspection data.

    This replaces the loose Dict[str, str | ModelSemVer | List[str] | ...] with
    proper type safety and clear field definitions. Uses the canonical
    ModelNodeCapabilities structure for capabilities data.
    """

    node_name: str = Field(default=..., description="Node name identifier")
    version: ModelSemVer = Field(
        default=..., description="Semantic version of the node"
    )
    capabilities: ModelNodeCapabilities = Field(
        default=..., description="Node capabilities"
    )
    tags: list[str] = Field(default_factory=list, description="Discovery tags")
    health_endpoint: str | None = Field(
        default=None, description="Health check endpoint"
    )
