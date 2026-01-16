"""Graph relationship model.

Type-safe model representing a relationship/edge in a graph database.

Thread Safety:
    ModelGraphRelationship instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelGraphRelationship(BaseModel):
    """
    Represents a relationship (edge) in a graph database.

    This model captures the structure of database relationships including
    their unique identifiers, type, properties, and connected node IDs.
    Designed for CRUD operations on graph databases.

    Thread Safety:
        This model is frozen (immutable) after creation, making it
        safe for concurrent read access across threads.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # ONEX_EXCLUDE: string_id - External database ID from Neo4j/Memgraph
    id: str = Field(
        default=...,
        description="Unique internal identifier for the relationship (database-assigned)",
    )
    # ONEX_EXCLUDE: string_id - Neo4j 5.x element ID format
    element_id: str = Field(
        default=...,
        description="Element ID for the relationship (Neo4j 5.x+ format)",
    )
    type: str = Field(
        default=...,
        description="Relationship type/label (e.g., 'DEPENDS_ON', 'CONTAINS')",
    )
    properties: SerializedDict = Field(
        default_factory=dict,
        description="Key-value properties stored on the relationship",
    )
    # ONEX_EXCLUDE: string_id - References external database node element ID
    start_node_id: str = Field(
        default=...,
        description="Element ID of the source/start node",
    )
    # ONEX_EXCLUDE: string_id - References external database node element ID
    end_node_id: str = Field(
        default=...,
        description="Element ID of the target/end node",
    )


__all__ = ["ModelGraphRelationship"]
