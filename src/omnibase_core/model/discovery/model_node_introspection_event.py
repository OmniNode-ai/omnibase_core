"""
Node Introspection Event Model

Event published by nodes on startup to announce their capabilities to the registry.
This enables pure event-driven service discovery.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.constants.event_types import CoreEventTypes
from omnibase_core.model.core.model_onex_event import ModelOnexEvent
from omnibase_core.model.core.model_semver import ModelSemVer


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


class ModelNodeIntrospectionEvent(ModelOnexEvent):
    """
    Event published by nodes to announce their capabilities for discovery.

    This event is automatically published by the MixinEventDrivenNode when a node
    starts up, enabling other services to discover its capabilities.
    """

    # Override event_type to be fixed for this event
    event_type: str = Field(
        default=CoreEventTypes.NODE_INTROSPECTION_EVENT,
        description="Event type identifier",
    )

    # Node identification
    node_name: str = Field(..., description="Name of the node (e.g. 'node_generator')")
    version: ModelSemVer = Field(..., description="Version of the node")

    # Node capabilities
    capabilities: ModelNodeCapabilities = Field(
        ...,
        description="Node capabilities including actions, protocols, and metadata",
    )

    # Discovery metadata
    health_endpoint: str | None = Field(
        None,
        description="Health check endpoint if available",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and discovery filtering",
    )

    # Consul-compatible fields for future adapter
    service_id: str | None = Field(
        None,
        description="Service ID for Consul compatibility (future)",
    )
    datacenter: str | None = Field(
        None,
        description="Datacenter for multi-DC discovery (future)",
    )

    @classmethod
    def create_from_node_info(
        cls,
        node_id: str,
        node_name: str,
        version: ModelSemVer,
        actions: list[str],
        protocols: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        **kwargs,
    ) -> "ModelNodeIntrospectionEvent":
        """
        Factory method to create introspection event from node information.

        Args:
            node_id: Unique node identifier
            node_name: Node name (e.g. 'node_generator')
            version: Node version
            actions: List of supported actions
            protocols: List of supported protocols
            metadata: Additional metadata
            tags: Discovery tags
            **kwargs: Additional fields

        Returns:
            ModelNodeIntrospectionEvent instance
        """
        capabilities = ModelNodeCapabilities(
            actions=actions,
            protocols=protocols or ["event_bus"],
            metadata=metadata or {},
        )

        return cls(
            node_id=node_id,
            node_name=node_name,
            version=version,
            capabilities=capabilities,
            tags=tags or [],
            **kwargs,
        )
