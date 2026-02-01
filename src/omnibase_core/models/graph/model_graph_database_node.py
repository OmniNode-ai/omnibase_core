"""Graph Database Node Model.

Type-safe model representing a node in a graph database (Neo4j, Memgraph, etc.).
Distinct from ModelGraphNode which is used for workflow visualization.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelGraphDatabaseNode(BaseModel):
    """
    Represents a node in a graph database.

    This model captures the structure of database nodes including
    their unique identifiers, labels, and properties. It is designed
    for CRUD operations on graph databases.

    Thread Safety:
        This model is frozen (immutable) after creation, making it
        safe for concurrent read access across threads.

    Note:
        This is distinct from ModelGraphNode which is used for
        workflow visualization in orchestrator graphs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # ONEX_EXCLUDE: string_id - External database ID from Neo4j/Memgraph, not ONEX-internal UUID
    id: str = Field(
        default=...,
        description="Unique internal identifier for the node (database-assigned)",
    )
    # ONEX_EXCLUDE: string_id - Neo4j 5.x element ID format (e.g., "4:abc-def:123")
    element_id: str = Field(
        default=...,
        description="Element ID for the node (Neo4j 5.x+ format)",
    )
    labels: list[str] = Field(
        default_factory=list,
        description="List of labels/types assigned to this node",
    )
    properties: SerializedDict = Field(
        default_factory=dict,
        description="Key-value properties stored on the node",
    )


__all__ = ["ModelGraphDatabaseNode"]
