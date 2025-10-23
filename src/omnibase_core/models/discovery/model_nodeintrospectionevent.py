from typing import Any, cast
from uuid import UUID

from pydantic import Field, field_validator

from omnibase_core.constants.event_types import NODE_INTROSPECTION_EVENT
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.nodes.model_node_capability import ModelNodeCapability
from omnibase_core.primitives.model_semver import ModelSemVer
from omnibase_core.utils.uuid_utilities import uuid_from_string


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
    service_id: UUID | None = Field(
        default=None,
        description="Service ID for Consul compatibility (future)",
    )
    datacenter: str | None = Field(
        default=None,
        description="Datacenter for multi-DC discovery (future)",
    )

    @field_validator("node_id", mode="before")
    @classmethod
    def convert_node_id_to_uuid(cls, v: Any) -> UUID:
        """Convert string node_id to UUID if needed."""
        if isinstance(v, str):
            return uuid_from_string(v, namespace="node")
        return cast(UUID, v)

    @field_validator("capabilities", mode="before")
    @classmethod
    def convert_capabilities(cls, v: Any) -> ModelNodeCapability:
        """Convert dict-like capabilities to ModelNodeCapability if needed."""
        if isinstance(v, ModelNodeCapability):
            return v

        # Handle dict-like object with actions, protocols, metadata
        if hasattr(v, "actions") or (isinstance(v, dict) and "actions" in v):
            actions = v.actions if hasattr(v, "actions") else v.get("actions", [])
            protocols = (
                v.protocols if hasattr(v, "protocols") else v.get("protocols", [])
            )
            metadata = v.metadata if hasattr(v, "metadata") else v.get("metadata", {})

            # Create a simple capability representation
            capability_str = f"capabilities_{','.join(actions)}"
            return ModelNodeCapability(
                value=capability_str.lower(),
                description=f"Node capabilities: {', '.join(actions)}",
                capability_display_name=capability_str.upper(),
            )

        return cast(ModelNodeCapability, v)

    @classmethod
    def create_from_node_info(
        cls,
        node_id: UUID | str,
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
            node_id: Unique node identifier (UUID or string)
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
        # Convert node_id to UUID if string
        if isinstance(node_id, str):
            node_id = uuid_from_string(node_id, namespace="node")

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
