"""
Graph Node Model

Type-safe graph node that replaces Dict[str, Any] usage
in orchestrator graphs.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_custom_fields import ModelCustomFields


class ModelGraphNode(BaseModel):
    """
    Type-safe graph node.

    Represents a node in an orchestrator graph with
    structured fields for common node attributes.
    """

    # Node identification
    node_id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Node display label")
    node_type: str = Field(
        ...,
        description="Type of node (e.g., 'start', 'end', 'process', 'decision')",
    )

    # Visual properties
    position_x: float | None = Field(
        None,
        description="X coordinate for visualization",
    )
    position_y: float | None = Field(
        None,
        description="Y coordinate for visualization",
    )
    color: str | None = Field(None, description="Node color for visualization")
    icon: str | None = Field(None, description="Node icon identifier")

    # Node data
    data: dict[str, Any] | None = Field(None, description="Node-specific data")
    properties: dict[str, str] | None = Field(None, description="Node properties")

    # Execution details (for executable nodes)
    node_name: str | None = Field(None, description="ONEX node name to execute")
    action: str | None = Field(None, description="Action to perform")
    inputs: dict[str, Any] | None = Field(None, description="Input parameters")

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
    description: str | None = Field(None, description="Node description")
    custom_fields: ModelCustomFields | None = Field(
        None,
        description="Custom fields for node-specific data",
    )
