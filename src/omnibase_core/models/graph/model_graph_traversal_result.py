"""Graph traversal result model.

Type-safe model representing the result of a graph traversal operation.

Thread Safety:
    ModelGraphTraversalResult instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.graph.model_graph_database_node import ModelGraphDatabaseNode
from omnibase_core.models.graph.model_graph_relationship import ModelGraphRelationship


class ModelGraphTraversalResult(BaseModel):
    """
    Represents the result of a graph traversal operation.

    Contains discovered nodes, relationships, paths, and execution metadata.
    Used for operations like BFS, DFS, shortest path, etc.

    Thread Safety:
        This model is frozen (immutable) after creation, making it
        safe for concurrent read access across threads.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    nodes: list[ModelGraphDatabaseNode] = Field(
        default_factory=list,
        description="List of nodes discovered during traversal",
    )
    relationships: list[ModelGraphRelationship] = Field(
        default_factory=list,
        description="List of relationships discovered during traversal",
    )
    paths: list[list[str]] = Field(
        default_factory=list,
        description="List of paths found, each path is a list of element IDs",
    )
    depth_reached: int = Field(
        default=0,
        description="Maximum depth reached during traversal",
        ge=0,
    )
    execution_time_ms: float = Field(
        default=0.0,
        description="Time taken to execute the traversal in milliseconds",
        ge=0.0,
    )


__all__ = ["ModelGraphTraversalResult"]
