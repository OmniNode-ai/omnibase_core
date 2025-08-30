"""
Model for MCP search responses.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelSearchDocument(BaseModel):
    """Model for individual search document."""

    content: str = Field(description="Document content")
    metadata: dict = Field(default_factory=dict, description="Document metadata")
    score: float = Field(description="Relevance score")
    collection: Optional[str] = Field(default=None, description="Source collection")


class ModelMCPSearchResult(BaseModel):
    """Model for MCP search results."""

    status: str = Field(description="Search status")
    results: List[ModelSearchDocument] = Field(
        default_factory=list, description="Search results"
    )
    total_results: int = Field(description="Total number of results")
    query: str = Field(description="Search query")
    collections_searched: List[str] = Field(
        default_factory=list, description="Collections searched"
    )
    error: Optional[str] = Field(default=None, description="Error message if any")
