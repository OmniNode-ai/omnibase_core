"""Retrieval statistics model with strong typing."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelRetrievalStatistics(BaseModel):
    """Strongly typed retrieval statistics model."""

    # Basic metrics
    total_queries: int = Field(ge=0, description="Total number of queries processed")
    successful_queries: int = Field(ge=0, description="Number of successful queries")
    failed_queries: int = Field(ge=0, description="Number of failed queries")

    # Performance metrics
    average_retrieval_time_ms: float = Field(
        ge=0.0,
        description="Average retrieval time in milliseconds",
    )
    total_documents_retrieved: int = Field(
        ge=0,
        description="Total documents retrieved",
    )
    average_documents_per_query: float = Field(
        ge=0.0,
        description="Average documents per query",
    )

    # Method breakdown
    bm25_queries: int = Field(ge=0, description="Number of BM25 queries")
    vector_queries: int = Field(ge=0, description="Number of vector queries")
    hybrid_queries: int = Field(ge=0, description="Number of hybrid queries")

    # Quality metrics
    average_relevance_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Average relevance score",
    )
    zero_result_queries: int = Field(
        ge=0,
        description="Number of queries with zero results",
    )

    # Cache metrics
    cache_hit_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Cache hit rate",
    )
    cache_miss_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Cache miss rate",
    )

    # Timing
    collection_start: datetime = Field(description="Statistics collection start time")
    collection_end: datetime = Field(description="Statistics collection end time")

    model_config = ConfigDict(frozen=True, extra="forbid")
