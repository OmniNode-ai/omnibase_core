"""
Graph Edge Model

Type-safe graph edge that replaces Dict[str, Any] usage
in orchestrator graphs.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field

from ..core.model_custom_fields import ModelCustomFields


class ModelGraphEdge(BaseModel):
    """
    Type-safe graph edge.

    Represents an edge in an orchestrator graph with
    structured fields for common edge attributes.
    """

    # Edge identification
    edge_id: str = Field(..., description="Unique edge identifier")
    source_node_id: str = Field(..., description="Source node ID")
    target_node_id: str = Field(..., description="Target node ID")

    # Edge properties
    label: Optional[str] = Field(None, description="Edge label")
    edge_type: Optional[str] = Field(
        None, description="Type of edge (e.g., 'normal', 'conditional', 'error')"
    )

    # Conditional logic
    condition: Optional[str] = Field(
        None, description="Condition expression for conditional edges"
    )
    priority: Optional[int] = Field(
        None, description="Edge priority for multiple outgoing edges"
    )

    # Visual properties
    color: Optional[str] = Field(None, description="Edge color for visualization")
    style: Optional[str] = Field(
        None, description="Edge style (e.g., 'solid', 'dashed', 'dotted')"
    )
    width: Optional[float] = Field(None, description="Edge width for visualization")

    # Data flow
    data_mapping: Optional[Dict[str, str]] = Field(
        None, description="Map source outputs to target inputs"
    )

    # Metadata
    description: Optional[str] = Field(None, description="Edge description")
    custom_fields: Optional[ModelCustomFields] = Field(
        None, description="Custom fields for edge-specific data"
    )
