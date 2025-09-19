"""Node announce metadata model for ONEX event-driven architecture."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_registry_execution_mode import RegistryExecutionModeEnum
from omnibase_core.enums.nodes import EnumNodeStatus

if TYPE_CHECKING:
    from omnibase_core.models.core.model_io_block import ModelIOBlock
    from omnibase_core.models.core.model_signature_block import ModelSignatureBlock

    from .model_node_metadata_block import (
        ModelNodeMetadataBlock,
    )


class ModelNodeAnnounceMetadata(BaseModel):
    """
    Metadata for NODE_ANNOUNCE events.

    This model contains all the information a node needs to announce itself
    to the registry, including its metadata block, status, capabilities, and nodes.
    """

    # Core identification
    node_id: str = Field(..., description="Unique identifier for the node")
    node_version: str | None = Field(None, description="Version of the node")

    # Node metadata and configuration
    metadata_block: "ModelNodeMetadataBlock" = Field(
        ...,
        description="Complete node metadata block from node.onex.yaml",
    )

    # Node status and operational state
    status: EnumNodeStatus | None = Field(
        default=EnumNodeStatus.ACTIVE,
        description="Current status of the node",
    )
    execution_mode: RegistryExecutionModeEnum | None = Field(
        default=RegistryExecutionModeEnum.MEMORY,
        description="Execution mode for the node",
    )

    # Input/Output configuration
    inputs: Optional["ModelIOBlock"] = Field(
        None,
        description="Node input configuration",
    )
    outputs: Optional["ModelIOBlock"] = Field(
        None,
        description="Node output configuration",
    )

    # Graph and trust configuration
    graph_binding: str | None = Field(
        None,
        description="Graph binding configuration",
    )
    trust_state: str | None = Field(None, description="Trust state of the node")

    # TTL and timing
    ttl: int | None = Field(None, description="Time to live in seconds")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the announcement",
    )

    # Schema and signature
    schema_version: str | None = Field(None, description="Schema version")
    signature_block: Optional["ModelSignatureBlock"] = Field(
        None,
        description="Signature block for verification",
    )

    # Correlation
    correlation_id: UUID | None = Field(
        None,
        description="Correlation ID for tracking",
    )


# Resolve forward references after all models are defined
try:
    # Import the models needed for forward references
    from omnibase_core.models.core.model_io_block import ModelIOBlock
    from omnibase_core.models.core.model_signature_block import ModelSignatureBlock

    from .model_node_metadata_block import (
        ModelNodeMetadataBlock,
    )

    # Rebuild the model to resolve forward references
    ModelNodeAnnounceMetadata.model_rebuild()
except ImportError:
    # If imports fail, continue without rebuilding (fallback mode)
    pass

# Compatibility alias
NodeAnnounceModelMetadata = ModelNodeAnnounceMetadata
