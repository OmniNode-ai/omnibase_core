"""Node announce metadata model for ONEX event-driven architecture."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_node_status import EnumNodeStatus
from omnibase_core.enums.enum_registry_execution_mode import EnumRegistryExecutionMode
from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.models.core.model_io_block import ModelIOBlock
    from omnibase_core.models.core.model_node_metadata_block import (
        ModelNodeMetadataBlock,
    )
    from omnibase_core.models.core.model_signature_block import ModelSignatureBlock


class ModelNodeAnnounceMetadata(BaseModel):
    """
    Metadata for NODE_ANNOUNCE events.

    This model contains all the information a node needs to announce itself
    to the registry, including its metadata block, status, capabilities, and tools.
    """

    # Core identification
    node_id: UUID = Field(default=..., description="Unique identifier for the node")
    node_version: ModelSemVer | None = Field(
        default=None, description="Version of the node"
    )

    # Node metadata and configuration
    metadata_block: "ModelNodeMetadataBlock" = Field(
        default=...,
        description="Complete node metadata block from node.onex.yaml",
    )

    # Node status and operational state
    status: EnumNodeStatus | None = Field(
        default=EnumNodeStatus.ACTIVE,
        description="Current status of the node",
    )
    execution_mode: EnumRegistryExecutionMode | None = Field(
        default=EnumRegistryExecutionMode.MEMORY,
        description="Execution mode for the node",
    )

    # Input/Output configuration
    inputs: "ModelIOBlock | None" = Field(
        default=None,
        description="Node input configuration",
    )
    outputs: "ModelIOBlock | None" = Field(
        default=None,
        description="Node output configuration",
    )

    # Graph and trust configuration
    graph_binding: str | None = Field(
        default=None,
        description="Graph binding configuration",
    )
    trust_state: str | None = Field(default=None, description="Trust state of the node")

    # TTL and timing
    ttl: int | None = Field(default=None, description="Time to live in seconds")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of the announcement",
    )

    # Schema and signature
    schema_version: ModelSemVer | None = Field(
        default=None, description="Schema version"
    )
    signature_block: "ModelSignatureBlock | None" = Field(
        default=None,
        description="Signature block for verification",
    )

    # Correlation
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracking",
    )


# Resolve forward references after all models are defined
try:
    # Import all models needed for forward references
    from omnibase_core.models.core.model_io_block import ModelIOBlock
    from omnibase_core.models.core.model_node_metadata_block import (
        ModelNodeMetadataBlock,
    )
    from omnibase_core.models.core.model_signature_block import ModelSignatureBlock

    # Rebuild the model to resolve forward references
    ModelNodeAnnounceMetadata.model_rebuild()
except ImportError:
    # If imports fail, continue without rebuilding (fallback mode)
    pass

# Compatibility alias
NodeAnnounceModelMetadata = ModelNodeAnnounceMetadata
