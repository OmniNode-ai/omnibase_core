"""
Node Reference Model.

Flexible node reference model that replaces EnumTargetNode
to support local, remote, and third-party node references.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_capability import ModelCapability
from omnibase_core.models.core.model_node_metadata import (
    NodeMetadataBlock as ModelNodeMetadata,
)


class ModelNodeReference(BaseModel):
    """
    Flexible node reference model.

    Supports local nodes, remote nodes, and third-party nodes
    with namespaces for isolation and extensibility.
    """

    node_name: str = Field(
        default=..., description="Node name", pattern="^[a-z][a-z0-9_]*$"
    )

    namespace: str | None = Field(
        default=None,
        description="Namespace for third-party isolation",
    )

    capabilities: list[ModelCapability] = Field(
        default_factory=list,
        description="Node capabilities",
    )

    node_type: str = Field(
        default="local",
        description="Node type (local, remote, plugin)",
    )

    endpoint: str | None = Field(default=None, description="Remote endpoint URL")

    metadata: ModelNodeMetadata | None = Field(
        default=None,
        description="Additional node metadata",
    )

    def get_qualified_name(self) -> str:
        """Get fully qualified node name including namespace."""
        if self.namespace:
            return f"{self.namespace}:{self.node_name}"
        return self.node_name

    def is_local(self) -> bool:
        """Check if this is a local node."""
        return self.node_type == "local"

    def is_remote(self) -> bool:
        """Check if this is a remote node."""
        return self.node_type == "remote"

    def is_third_party(self) -> bool:
        """Check if this is a third-party node."""
        return self.namespace is not None and self.namespace != "onex"

    def has_capability(self, capability: ModelCapability) -> bool:
        """Check if node has a specific capability."""
        return any(cap.matches(capability) for cap in self.capabilities)

    @classmethod
    def create_local(
        cls,
        node_name: str,
        capabilities: list[ModelCapability] | None = None,
    ) -> "ModelNodeReference":
        """Create a local node reference."""
        return cls(
            node_name=node_name,
            node_type="local",
            capabilities=capabilities if capabilities is not None else [],
        )

    @classmethod
    def create_remote(
        cls,
        node_name: str,
        endpoint: str,
        capabilities: list[ModelCapability] | None = None,
    ) -> "ModelNodeReference":
        """Create a remote node reference."""
        return cls(
            node_name=node_name,
            node_type="remote",
            endpoint=endpoint,
            capabilities=capabilities if capabilities is not None else [],
        )

    @classmethod
    def create_with_namespace(
        cls,
        node_name: str,
        namespace: str,
        capabilities: list[ModelCapability] | None = None,
    ) -> "ModelNodeReference":
        """Create a node reference with namespace."""
        return cls(
            node_name=node_name,
            namespace=namespace,
            node_type="plugin",
            capabilities=capabilities if capabilities is not None else [],
        )
