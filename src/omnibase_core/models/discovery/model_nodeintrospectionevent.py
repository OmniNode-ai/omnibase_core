from typing import Any, cast
from uuid import UUID

from pydantic import Field, field_validator

from omnibase_core.constants.constants_event_types import NODE_INTROSPECTION_EVENT
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.node_metadata.model_node_capability import ModelNodeCapability
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_uuid_utilities import uuid_from_string


class ModelNodeIntrospectionEvent(ModelOnexEvent):
    """
    Event published by nodes to announce their capabilities for discovery.

    This event is automatically published by the MixinEventDrivenNode when a node
    starts up, enabling other services to discover its capabilities.

    ONEX Architecture:
        The 4-node ONEX architecture classifies nodes by their primary function:
        - effect: External I/O, APIs, databases, side effects
        - compute: Pure transformations, algorithmic processing
        - reducer: Aggregation, persistence, state management
        - orchestrator: Workflow coordination, multi-step execution

        node_type enforces this 4-node architecture.
        node_role provides optional specialization within a type (e.g., registry, adapter).

    Example:
        Registry node:
            node_type="effect" (primary function: external I/O)
            node_role="registry" (specialization within effect nodes)
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
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the node",
    )

    # ONEX Architecture Classification
    node_type: str = Field(
        default=...,
        description="Type of ONEX node based on primary function",
        pattern="^(effect|compute|reducer|orchestrator)$",
    )
    node_role: str | None = Field(
        default=None,
        description="Optional role specialization within node type (e.g., 'registry', 'adapter', 'bridge')",
    )

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
        return cast("UUID", v)

    @field_validator("capabilities", mode="before")
    @classmethod
    def convert_capabilities(cls, v: Any) -> ModelNodeCapability:
        """Convert dict-like capabilities to ModelNodeCapability if needed."""
        if isinstance(v, ModelNodeCapability):
            return v

        # Handle dict-like object with actions
        # Note: The source object may contain 'protocols' (list of protocol interfaces
        # the node implements, e.g., ProtocolEventBus) and 'metadata' (node-level
        # metadata dict) fields. These are intentionally ignored because
        # ModelNodeCapability represents a single capability definition, not a full
        # node specification. Future versions may extend ModelNodeCapability or
        # introduce a separate model to capture protocol implementations.
        if hasattr(v, "actions") or (isinstance(v, dict) and "actions" in v):
            actions = v.actions if hasattr(v, "actions") else v.get("actions", [])

            # Create a simple capability representation
            capability_str = f"capabilities_{','.join(actions)}"
            return ModelNodeCapability(
                value=capability_str.lower(),
                description=f"Node capabilities: {', '.join(actions)}",
                capability_display_name=capability_str.upper(),
                version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            )

        return cast("ModelNodeCapability", v)

    @classmethod
    def create_from_node_info(
        cls,
        node_id: UUID | str,
        node_name: str,
        version: ModelSemVer,
        node_type: str,
        actions: list[str],
        tags: list[str] | None = None,
        node_role: str | None = None,
        **kwargs: Any,
    ) -> "ModelNodeIntrospectionEvent":
        """
        Factory method to create introspection event from node information.

        Args:
            node_id: Unique node identifier (UUID or string)
            node_name: Node name (e.g. 'node_generator')
            version: Node version
            node_type: Type of ONEX node (effect, compute, reducer, orchestrator)
            actions: List of supported actions
            tags: Discovery tags
            node_role: Optional role specialization (registry, adapter, bridge, etc.)
            **kwargs: Additional fields (e.g., health_endpoint, correlation_id)

        Returns:
            ModelNodeIntrospectionEvent instance

        Note:
            Previously accepted 'protocols' and 'metadata' parameters but these were
            never used since ModelNodeCapability doesn't support them and the base
            model has extra="forbid" configured. Callers passing these parameters
            need to be updated.
        """
        # Convert node_id to UUID if string
        if isinstance(node_id, str):
            node_id = uuid_from_string(node_id, namespace="node")

        capabilities = ModelNodeCapability(
            value=f"node_{node_name.lower()}_capabilities",
            description=f"Capabilities for {node_name}: {', '.join(actions)}",
            capability_display_name=f"{node_name.upper()}_CAPABILITIES",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        return cls(
            node_id=node_id,
            node_name=node_name,
            version=version,
            node_type=node_type,
            capabilities=capabilities,
            tags=tags if tags is not None else [],
            node_role=node_role,
            **kwargs,
        )
