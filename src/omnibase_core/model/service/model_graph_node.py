"""
Graph Node Model

Type-safe graph node that replaces Dict[str, Any] usage
in orchestrator graphs.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..core.model_custom_fields import ModelCustomFields


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
        ..., description="Type of node (e.g., 'start', 'end', 'process', 'decision')"
    )

    # Visual properties
    position_x: Optional[float] = Field(
        None, description="X coordinate for visualization"
    )
    position_y: Optional[float] = Field(
        None, description="Y coordinate for visualization"
    )
    color: Optional[str] = Field(None, description="Node color for visualization")
    icon: Optional[str] = Field(None, description="Node icon identifier")

    # Node data
    data: Optional[Dict[str, Any]] = Field(None, description="Node-specific data")
    properties: Optional[Dict[str, str]] = Field(None, description="Node properties")

    # Execution details (for executable nodes)
    node_name: Optional[str] = Field(None, description="ONEX node name to execute")
    action: Optional[str] = Field(None, description="Action to perform")
    inputs: Optional[Dict[str, Any]] = Field(None, description="Input parameters")

    # Graph relationships (may be redundant with edges)
    incoming_edges: List[str] = Field(
        default_factory=list, description="IDs of incoming edges"
    )
    outgoing_edges: List[str] = Field(
        default_factory=list, description="IDs of outgoing edges"
    )

    # Metadata
    description: Optional[str] = Field(None, description="Node description")
    custom_fields: Optional[ModelCustomFields] = Field(
        None, description="Custom fields for node-specific data"
    )
