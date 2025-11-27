from pydantic import Field

__all__ = [
    "ModelNodeCapabilities",
    "ModelNodeIntrospectionEvent",
]

"""
Node Introspection Event Model

Event published by nodes on startup to announce their capabilities to the registry.
This enables pure event-driven service discovery.
"""

from typing import Any

from pydantic import BaseModel

from .model_nodeintrospectionevent import ModelNodeIntrospectionEvent


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
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional node metadata (author, trust_score, etc.)",
    )
