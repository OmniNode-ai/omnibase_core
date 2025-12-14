"""
Graph Edge Model

Type-safe graph edge that replaces Dict[str, Any] usage
in orchestrator graphs.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.services.model_custom_fields import ModelCustomFields


class ModelGraphEdge(BaseModel):
    """
    Type-safe graph edge.

    Represents an edge in an orchestrator graph with
    structured fields for common edge attributes.
    """

    # Edge identification
    edge_id: UUID = Field(default=..., description="Unique edge identifier")
    source_node_id: UUID = Field(default=..., description="Source node ID")
    target_node_id: UUID = Field(default=..., description="Target node ID")

    # Edge properties
    label: str | None = Field(default=None, description="Edge label")
    edge_type: str | None = Field(
        default=None,
        description="Type of edge (e.g., 'normal', 'conditional', 'error')",
    )

    # Conditional logic
    condition: str | None = Field(
        default=None,
        description="Condition expression for conditional edges",
    )
    priority: int | None = Field(
        default=None,
        description="Edge priority for multiple outgoing edges",
    )

    # Visual properties
    color: str | None = Field(default=None, description="Edge color for visualization")
    style: str | None = Field(
        default=None,
        description="Edge style (e.g., 'solid', 'dashed', 'dotted')",
    )
    width: float | None = Field(
        default=None, description="Edge width for visualization"
    )

    # Data flow
    data_mapping: dict[str, str] | None = Field(
        default=None,
        description="Map source outputs to target inputs",
    )

    # Metadata
    description: str | None = Field(default=None, description="Edge description")
    custom_fields: ModelCustomFields | None = Field(
        default=None,
        description="Custom fields for edge-specific data",
    )
