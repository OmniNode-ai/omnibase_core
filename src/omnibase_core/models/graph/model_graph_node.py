"""
Graph Node Model

Type-safe graph node that replaces Dict[str, Any] usage
in orchestrator graphs.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.services.model_custom_fields import ModelCustomFields
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelGraphNode(BaseModel):
    """
    Type-safe graph node.

    Represents a node in an orchestrator graph with
    structured fields for common node attributes.
    """

    # Node identification
    node_id: UUID = Field(default=..., description="Unique node identifier")
    label: str = Field(default=..., description="Node display label")
    node_type: str = Field(
        default=...,
        description="Type of node (e.g., 'start', 'end', 'process', 'decision')",
    )

    # Visual properties
    position_x: float | None = Field(
        default=None,
        description="X coordinate for visualization",
    )
    position_y: float | None = Field(
        default=None,
        description="Y coordinate for visualization",
    )
    color: str | None = Field(default=None, description="Node color for visualization")
    icon: str | None = Field(default=None, description="Node icon identifier")

    # Node data - uses SerializedDict for JSON-serializable node data
    data: SerializedDict | None = Field(default=None, description="Node-specific data")
    properties: dict[str, str] | None = Field(
        default=None, description="Node properties"
    )

    # Execution details (for executable nodes)
    node_name: str | None = Field(default=None, description="ONEX node name to execute")
    action: str | None = Field(default=None, description="Action to perform")
    # Uses SerializedDict for JSON-serializable input parameters
    inputs: SerializedDict | None = Field(default=None, description="Input parameters")

    # Graph relationships (may be redundant with edges)
    incoming_edges: list[str] = Field(
        default_factory=list,
        description="IDs of incoming edges",
    )
    outgoing_edges: list[str] = Field(
        default_factory=list,
        description="IDs of outgoing edges",
    )

    # Metadata
    description: str | None = Field(default=None, description="Node description")
    custom_fields: ModelCustomFields | None = Field(
        default=None,
        description="Custom fields for node-specific data",
    )
