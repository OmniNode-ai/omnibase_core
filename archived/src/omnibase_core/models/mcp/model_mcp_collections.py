"""
Model for MCP Qdrant collections response.
"""

from pydantic import BaseModel, Field


class ModelQdrantCollection(BaseModel):
    """Model for individual Qdrant collection."""

    name: str = Field(description="Collection name")
    vector_count: int = Field(description="Number of vectors in collection")
    config: dict = Field(default_factory=dict, description="Collection configuration")


class ModelMCPCollections(BaseModel):
    """Model for MCP Qdrant collections response."""

    status: str = Field(description="Query status")
    collections: list[ModelQdrantCollection] = Field(
        default_factory=list,
        description="Qdrant collections",
    )
    total_collections: int = Field(description="Total number of collections")
    error: str | None = Field(default=None, description="Error message if any")
