"""
Retrieval operation statistics model.

Provides strongly-typed statistics to replace Dict[str, Any] usage.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelRetrievalOperationStatistics(BaseModel):
    """
    Statistics about retrieval operation.

    Replaces Dict[str, Any] usage in retrieval_statistics fields.
    """

    total_documents_searched: int = Field(
        default=0,
        description="Total number of documents in search index",
    )

    documents_returned: int = Field(
        default=0,
        description="Number of documents returned in results",
    )

    bm25_search_time_ms: int | None = Field(
        default=None,
        description="Time spent on BM25 search in milliseconds",
    )

    vector_search_time_ms: int | None = Field(
        default=None,
        description="Time spent on vector search in milliseconds",
    )

    fusion_time_ms: int | None = Field(
        default=None,
        description="Time spent combining results in milliseconds",
    )

    total_search_time_ms: int | None = Field(
        default=None,
        description="Total search time in milliseconds",
    )

    cache_hit_count: int = Field(
        default=0,
        description="Number of results served from cache",
    )

    cache_miss_count: int = Field(
        default=0,
        description="Number of results not found in cache",
    )

    index_size: int | None = Field(default=None, description="Size of search index")

    query_expansion_terms_added: int = Field(
        default=0,
        description="Number of terms added during query expansion",
    )

    filters_applied: int = Field(
        default=0,
        description="Number of filters applied to search",
    )

    documents_filtered_out: int = Field(
        default=0,
        description="Number of documents removed by filters",
    )

    average_document_score: float | None = Field(
        default=None,
        description="Average relevance score of returned documents",
    )

    max_document_score: float | None = Field(
        default=None,
        description="Highest relevance score in results",
    )

    min_document_score: float | None = Field(
        default=None,
        description="Lowest relevance score in results",
    )

    memory_usage_mb: float | None = Field(
        default=None,
        description="Peak memory usage during search in MB",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
