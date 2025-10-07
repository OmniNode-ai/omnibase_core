from typing import Any, List
from uuid import UUID

from pydantic import Field

from omnibase_core.constants.event_types import NODE_INTROSPECTION_EVENT
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.core.model_semver import ModelSemVer
from omnibase_core.models.nodes.model_node_capability import ModelNodeCapability


class ModelNodeIntrospectionEvent(ModelOnexEvent):
    """
    Event published by nodes to announce their capabilities for discovery.

    This event is automatically published by the MixinEventDrivenNode when a node
    starts up, enabling other services to discover its capabilities.
    """

    # Override event_type to be fixed for this event
    event_type: str = Field(
        default=NODE_INTROSPECTION_EVENT,
        description="Event type identifier",
    )

    # Node identification
    node_name: str = Field(
        default=..., description="Name of the node (e.g. 'node_generator')"
    )
    version: ModelSemVer = Field(default=..., description="Version of the node")

    # Node capabilities
    capabilities: ModelNodeCapability = Field(
        default=...,
        description="Node capabilities including actions, protocols, and metadata",
    )

    # Discovery metadata
    health_endpoint: str | None = Field(
        default=None,
        description="Health check endpoint if available",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and discovery filtering",
    )

    # Consul-compatible fields for future adapter
    service_id: str | None = Field(
        default=None,
        description="Service ID for Consul compatibility (future)",
    )
    datacenter: str | None = Field(
        default=None,
        description="Datacenter for multi-DC discovery (future)",
    )

    @classmethod
    def create_from_node_info(
        cls,
        node_id: UUID,
        node_name: str,
        version: ModelSemVer,
        actions: list[str],
        protocols: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
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
        capabilities = ModelNodeCapability(
            value=f"node_{node_name.lower()}_capabilities",
            description=f"Capabilities for {node_name}: {', '.join(actions)}",
            capability_display_name=f"{node_name.upper()}_CAPABILITIES",
        )

        return cls(
            node_id=node_id,
            node_name=node_name,
            version=version,
            capabilities=capabilities,
            tags=tags or [],
            **kwargs,
        )
