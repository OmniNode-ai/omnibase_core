"""
Node Introspection Event Model

Event published by nodes on startup to announce their capabilities to the registry.
This enables pure event-driven service discovery.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_typed_metadata import (
    ModelNodeCapabilitiesMetadata,
)

from .model_nodeintrospectionevent import ModelNodeIntrospectionEvent

__all__ = [
    "ModelNodeCapabilities",
    "ModelNodeIntrospectionEvent",
]


class ModelNodeCapabilities(BaseModel):
    """Node capabilities data structure"""

    actions: list[str] = Field(
        default_factory=list,
        description="List of actions this node supports",
    )
    protocols: list[str] = Field(
        default_factory=list,
        description="List of protocols this node supports (mcp, graphql, event_bus)",
    )
    metadata: ModelNodeCapabilitiesMetadata = Field(
        default_factory=ModelNodeCapabilitiesMetadata,
        description="Additional node metadata (author, trust_score, etc.)",
    )
