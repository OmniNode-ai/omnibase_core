"""Graph handler metadata model.

Type-safe model representing metadata about a graph database handler.

Thread Safety:
    ModelGraphHandlerMetadata instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelGraphHandlerMetadata(BaseModel):
    """
    Represents metadata about a graph database handler.

    Contains information about the handler's capabilities,
    database type, and supported features.

    Thread Safety:
        This model is frozen (immutable) after creation, making it
        safe for concurrent read access across threads.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    handler_type: str = Field(
        default=...,
        description="Type of graph handler (e.g., 'neo4j', 'memgraph', 'neptune')",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of supported capabilities (e.g., 'cypher', 'gremlin', 'apoc')",
    )
    database_type: str = Field(
        default=...,
        description="Type of graph database (e.g., 'property_graph', 'rdf')",
    )
    supports_transactions: bool = Field(
        default=True,
        description="Whether the handler supports transactional operations",
    )


__all__ = ["ModelGraphHandlerMetadata"]
