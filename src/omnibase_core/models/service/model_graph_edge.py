from typing import Dict

from pydantic import Field

"""
Graph Edge Model

Type-safe graph edge that replaces Dict[str, Any] usage
in orchestrator graphs.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_custom_fields import ModelCustomFields


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
    label: str | None = Field(None, description="Edge label")
    edge_type: str | None = Field(
        None,
        description="Type of edge (e.g., 'normal', 'conditional', 'error')",
    )

    # Conditional logic
    condition: str | None = Field(
        None,
        description="Condition expression for conditional edges",
    )
    priority: int | None = Field(
        None,
        description="Edge priority for multiple outgoing edges",
    )

    # Visual properties
    color: str | None = Field(None, description="Edge color for visualization")
    style: str | None = Field(
        None,
        description="Edge style (e.g., 'solid', 'dashed', 'dotted')",
    )
    width: float | None = Field(None, description="Edge width for visualization")

    # Data flow
    data_mapping: dict[str, str] | None = Field(
        None,
        description="Map source outputs to target inputs",
    )

    # Metadata
    description: str | None = Field(None, description="Edge description")
    custom_fields: ModelCustomFields | None = Field(
        None,
        description="Custom fields for edge-specific data",
    )
