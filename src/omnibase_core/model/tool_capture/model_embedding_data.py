"""
Embedding data models for Tool Capture Embeddings Service.

Represents embedding metadata, search results, and statistics.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ModelEmbeddingMetadata(BaseModel):
    """Metadata associated with an embedding."""

    source_type: str = Field(..., description="Type of source content")
    source_id: str = Field(..., description="ID of the source content")
    conversation_id: str = Field(..., description="Associated conversation ID")
    content_type: str = Field(..., description="Type of content embedded")
    content_length: int = Field(..., description="Length of original content")
    embedding_model: str = Field(
        "mxbai-embed-large", description="Model used for embedding"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the embedding was created"
    )


class ModelEmbeddingSearchResult(BaseModel):
    """Search result from embedding similarity search."""

    embedding_id: str = Field(..., description="Unique embedding identifier")
    source_type: str = Field(..., description="Type of source content")
    source_id: str = Field(..., description="ID of the source content")
    conversation_id: str = Field(..., description="Associated conversation ID")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    content_snippet: Optional[str] = Field(
        None, description="Optional snippet of original content"
    )
    metadata: ModelEmbeddingMetadata = Field(
        ..., description="Associated embedding metadata"
    )


class ModelEmbeddingStatistics(BaseModel):
    """Statistics for embedding storage and operations."""

    total_embeddings: int = Field(..., description="Total number of stored embeddings")
    embeddings_by_type: dict[str, int] = Field(
        default_factory=dict, description="Count of embeddings by source type"
    )
    total_conversations: int = Field(
        ..., description="Total unique conversations with embeddings"
    )
    average_embedding_time_ms: float = Field(
        ..., description="Average time to create embeddings in milliseconds"
    )
    storage_size_mb: float = Field(..., description="Total storage size in megabytes")
    last_embedding_created: Optional[datetime] = Field(
        None, description="Timestamp of most recent embedding"
    )


class ModelSimilaritySearchResult(BaseModel):
    """Result from similarity search operations."""

    query: str = Field(..., description="Original search query")
    results: List[ModelEmbeddingSearchResult] = Field(
        ..., description="List of similar embeddings"
    )
    search_time_ms: float = Field(..., description="Time taken for search in ms")
    total_results: int = Field(..., description="Total number of results found")


class ModelConversationRecommendation(BaseModel):
    """Recommendation based on conversation similarity."""

    user_message: ModelEmbeddingSearchResult = Field(
        ..., description="Similar user message found"
    )
    similar_responses: List[ModelEmbeddingSearchResult] = Field(
        ..., description="Similar Claude responses"
    )
    recommendation_score: float = Field(..., description="Overall recommendation score")
