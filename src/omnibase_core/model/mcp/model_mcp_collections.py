"""
Model for MCP Qdrant collections response.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelQdrantCollection(BaseModel):
    """Model for individual Qdrant collection."""

    name: str = Field(description="Collection name")
    vector_count: int = Field(description="Number of vectors in collection")
    config: dict = Field(default_factory=dict, description="Collection configuration")


class ModelMCPCollections(BaseModel):
    """Model for MCP Qdrant collections response."""

    status: str = Field(description="Query status")
    collections: List[ModelQdrantCollection] = Field(
        default_factory=list, description="Qdrant collections"
    )
    total_collections: int = Field(description="Total number of collections")
    error: Optional[str] = Field(default=None, description="Error message if any")
