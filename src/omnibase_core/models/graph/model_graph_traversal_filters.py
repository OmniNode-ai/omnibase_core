"""Graph Traversal Filters Model.

Type-safe model for configuring graph traversal filter criteria.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelGraphTraversalFilters(BaseModel):
    """
    Represents filter criteria for graph traversal operations.

    Contains filters for node labels, node properties, and
    relationship properties to constrain traversal scope.

    Thread Safety:
        This model is frozen (immutable) after creation, making it
        safe for concurrent read access across threads.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node_labels: list[str] = Field(
        default_factory=list,
        description="List of node labels to include in traversal",
    )
    node_properties: SerializedDict = Field(
        default_factory=dict,
        description="Node property filters (key-value pairs to match)",
    )
    relationship_types: list[str] = Field(
        default_factory=list,
        description="List of relationship types to traverse",
    )
    relationship_properties: SerializedDict = Field(
        default_factory=dict,
        description="Relationship property filters (key-value pairs to match)",
    )


__all__ = ["ModelGraphTraversalFilters"]
