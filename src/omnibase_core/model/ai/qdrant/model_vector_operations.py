"""
Pydantic models for Qdrant vector database operations.

This module defines the data models used for vector operations, search results,
and collection management within the Qdrant vector database integration.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ModelVectorPoint(BaseModel):
    """Model representing a vector point for Qdrant operations."""

    point_id: str | int = Field(
        ...,
        description="Unique identifier for the vector point",
    )
    vector: list[float] = Field(..., description="Vector embedding values")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata payload for the vector",
    )

    @field_validator("vector")
    @classmethod
    def validate_vector(cls, v):
        if not v:
            msg = "Vector cannot be empty"
            raise ValueError(msg)
        if not all(isinstance(x, int | float) for x in v):
            msg = "Vector must contain only numeric values"
            raise ValueError(msg)
        return v


class ModelVectorSearchQuery(BaseModel):
    """Model representing a vector similarity search query."""

    query_vector: list[float] = Field(
        ...,
        description="Query vector for similarity search",
    )
    collection_name: str = Field(..., description="Name of the collection to search")
    limit: int = Field(default=10, description="Maximum number of results to return")
    score_threshold: float | None = Field(
        None,
        description="Minimum similarity score threshold",
    )
    filter_conditions: dict[str, Any] | None = Field(
        None,
        description="Metadata filter conditions",
    )
    with_payload: bool = Field(
        default=True,
        description="Include payload in search results",
    )
    with_vectors: bool = Field(
        default=False,
        description="Include vectors in search results",
    )

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v):
        if v <= 0 or v > 10000:
            msg = "Limit must be between 1 and 10000"
            raise ValueError(msg)
        return v

    @field_validator("score_threshold")
    @classmethod
    def validate_score_threshold(cls, v):
        if v is not None and not 0.0 <= v <= 1.0:
            msg = "Score threshold must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelVectorSearchResult(BaseModel):
    """Model representing a single vector search result."""

    point_id: str | int = Field(
        ...,
        description="ID of the matching vector point",
    )
    score: float = Field(..., description="Similarity score for the match")
    payload: dict[str, Any] | None = Field(
        None,
        description="Metadata payload of the result",
    )
    vector: list[float] | None = Field(
        None,
        description="Vector values if requested",
    )

    @field_validator("score")
    @classmethod
    def validate_score(cls, v):
        if not 0.0 <= v <= 1.0:
            msg = "Score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelVectorSearchResponse(BaseModel):
    """Model representing the complete vector search response."""

    results: list[ModelVectorSearchResult] = Field(
        ...,
        description="List of search results",
    )
    query_time_ms: float = Field(
        ...,
        description="Query execution time in milliseconds",
    )
    total_count: int = Field(..., description="Total number of matching vectors")
    collection_info: dict[str, Any] = Field(
        default_factory=dict,
        description="Collection metadata",
    )
    search_query: ModelVectorSearchQuery = Field(
        ...,
        description="Original search query",
    )


class ModelVectorBatchOperation(BaseModel):
    """Model representing a batch vector operation."""

    operation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique operation identifier",
    )
    operation_type: str = Field(
        ...,
        description="Type of batch operation (insert, update, delete)",
    )
    collection_name: str = Field(..., description="Target collection name")
    points: list[ModelVectorPoint] = Field(
        default_factory=list,
        description="Vector points for the operation",
    )
    batch_size: int = Field(default=100, description="Batch processing size")
    parallel_workers: int = Field(default=4, description="Number of parallel workers")

    @field_validator("operation_type")
    @classmethod
    def validate_operation_type(cls, v):
        allowed_types = ["insert", "update", "delete", "upsert"]
        if v not in allowed_types:
            msg = f"Operation type must be one of {allowed_types}"
            raise ValueError(msg)
        return v

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v):
        if v <= 0 or v > 1000:
            msg = "Batch size must be between 1 and 1000"
            raise ValueError(msg)
        return v


class ModelVectorBatchResult(BaseModel):
    """Model representing the result of a batch vector operation."""

    operation_id: str = Field(..., description="Operation identifier")
    success_count: int = Field(default=0, description="Number of successful operations")
    failure_count: int = Field(default=0, description="Number of failed operations")
    total_count: int = Field(..., description="Total number of operations attempted")
    execution_time_ms: float = Field(
        ...,
        description="Total execution time in milliseconds",
    )
    failed_points: list[str] = Field(
        default_factory=list,
        description="IDs of points that failed processing",
    )
    error_messages: list[str] = Field(
        default_factory=list,
        description="Error messages from failed operations",
    )

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100.0


class ModelQdrantConnectionConfig(BaseModel):
    """Model representing Qdrant database connection configuration."""

    host: str = Field(default="localhost", description="Qdrant server host")
    port: int = Field(default=6333, description="Qdrant server port")
    grpc_port: int | None = Field(
        None,
        description="Qdrant gRPC port for high-performance operations",
    )
    https: bool = Field(default=False, description="Use HTTPS connection")
    api_key: str | None = Field(None, description="API key for authentication")
    timeout: float = Field(default=30.0, description="Connection timeout in seconds")
    retry_count: int = Field(default=3, description="Number of retry attempts")
    pool_size: int = Field(default=10, description="Connection pool size")

    @field_validator("port", "grpc_port")
    @classmethod
    def validate_port(cls, v):
        if v is not None and not 1 <= v <= 65535:
            msg = "Port must be between 1 and 65535"
            raise ValueError(msg)
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v):
        if v <= 0:
            msg = "Timeout must be positive"
            raise ValueError(msg)
        return v


class ModelQdrantHealthStatus(BaseModel):
    """Model representing Qdrant database health status."""

    is_healthy: bool = Field(..., description="Overall health status")
    response_time_ms: float = Field(..., description="Health check response time")
    version: str | None = Field(None, description="Qdrant server version")
    collections_count: int = Field(default=0, description="Number of collections")
    total_vectors: int = Field(
        default=0,
        description="Total number of vectors across all collections",
    )
    memory_usage_mb: float | None = Field(
        None,
        description="Memory usage in megabytes",
    )
    disk_usage_mb: float | None = Field(None, description="Disk usage in megabytes")
    cluster_status: str | None = Field(None, description="Cluster health status")
    last_check_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last health check timestamp",
    )


class ModelQdrantPerformanceMetrics(BaseModel):
    """Model representing Qdrant performance metrics."""

    collection_name: str = Field(..., description="Collection name for metrics")
    total_vectors: int = Field(..., description="Total number of vectors in collection")
    index_size_mb: float = Field(..., description="Index size in megabytes")
    average_search_time_ms: float = Field(
        ...,
        description="Average search time in milliseconds",
    )
    queries_per_second: float = Field(
        default=0.0,
        description="Queries per second throughput",
    )
    insertions_per_second: float = Field(
        default=0.0,
        description="Insertions per second throughput",
    )
    memory_usage_mb: float = Field(..., description="Memory usage for this collection")
    last_optimization_time: datetime | None = Field(
        None,
        description="Last index optimization timestamp",
    )
    cache_hit_rate: float = Field(default=0.0, description="Cache hit rate percentage")

    @field_validator("cache_hit_rate")
    @classmethod
    def validate_cache_hit_rate(cls, v):
        if not 0.0 <= v <= 100.0:
            msg = "Cache hit rate must be between 0.0 and 100.0"
            raise ValueError(msg)
        return v


class FilterOperator(str, Enum):
    """Enumeration of supported filter operators."""

    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    IN = "in"
    NOT_IN = "nin"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    RANGE = "range"
    TEXT_MATCH = "text_match"
    REGEX = "regex"


class ModelFilterCondition(BaseModel):
    """Model representing a single filter condition."""

    field: str = Field(..., description="Field name to filter on")
    operator: FilterOperator = Field(..., description="Filter operator")
    value: Any = Field(..., description="Filter value")
    case_sensitive: bool = Field(
        default=True,
        description="Case sensitivity for text operations",
    )

    @field_validator("value")
    @classmethod
    def validate_value(cls, v, info):
        operator = info.data.get("operator")
        if operator in [FilterOperator.IN, FilterOperator.NOT_IN] and not isinstance(
            v,
            list,
        ):
            msg = "IN and NOT_IN operators require a list value"
            raise ValueError(msg)
        if operator == FilterOperator.RANGE and not isinstance(v, dict):
            msg = "RANGE operator requires a dict with 'min' and/or 'max' keys"
            raise ValueError(
                msg,
            )
        return v


class ModelMetadataFilter(BaseModel):
    """Model representing complex metadata filtering."""

    conditions: list[ModelFilterCondition] = Field(
        ...,
        description="List of filter conditions",
    )
    logical_operator: Literal["AND", "OR"] = Field(
        default="AND",
        description="Logical operator for combining conditions",
    )
    nested_filters: list["ModelMetadataFilter"] | None = Field(
        None,
        description="Nested filter groups",
    )

    @field_validator("conditions")
    @classmethod
    def validate_conditions(cls, v):
        if not v:
            msg = "At least one filter condition is required"
            raise ValueError(msg)
        return v


class SearchMode(str, Enum):
    """Enumeration of search modes."""

    VECTOR_ONLY = "vector_only"
    METADATA_ONLY = "metadata_only"
    HYBRID = "hybrid"
    RERANK = "rerank"


class ModelHybridSearchQuery(BaseModel):
    """Model representing a hybrid search query combining vector and metadata search."""

    collection_name: str = Field(..., description="Name of the collection to search")

    # Vector search parameters
    query_vector: list[float] | None = Field(
        None,
        description="Query vector for similarity search",
    )
    vector_weight: float = Field(
        default=0.7,
        description="Weight for vector similarity score",
    )

    # Text/keyword search parameters
    text_query: str | None = Field(None, description="Text query for keyword search")
    text_fields: list[str] = Field(
        default_factory=list,
        description="Fields to search for text query",
    )
    text_weight: float = Field(default=0.3, description="Weight for text search score")

    # Metadata filtering
    metadata_filter: ModelMetadataFilter | None = Field(
        None,
        description="Metadata filtering conditions",
    )

    # Search configuration
    search_mode: SearchMode = Field(
        default=SearchMode.HYBRID,
        description="Search mode",
    )
    limit: int = Field(default=10, description="Maximum number of results to return")
    score_threshold: float | None = Field(
        None,
        description="Minimum combined score threshold",
    )

    # Result configuration
    with_payload: bool = Field(
        default=True,
        description="Include payload in search results",
    )
    with_vectors: bool = Field(
        default=False,
        description="Include vectors in search results",
    )
    with_explanation: bool = Field(
        default=False,
        description="Include score explanation",
    )

    @field_validator("vector_weight", "text_weight")
    @classmethod
    def validate_weights(cls, v):
        if not 0.0 <= v <= 1.0:
            msg = "Weights must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v):
        if v <= 0 or v > 10000:
            msg = "Limit must be between 1 and 10000"
            raise ValueError(msg)
        return v

    def model_post_init(self, __context):
        """Validate that at least one search method is specified."""
        if self.search_mode == SearchMode.VECTOR_ONLY and not self.query_vector:
            msg = "Vector search requires query_vector"
            raise ValueError(msg)
        if (
            self.search_mode == SearchMode.METADATA_ONLY
            and not self.metadata_filter
            and not self.text_query
        ):
            msg = "Metadata search requires metadata_filter or text_query"
            raise ValueError(msg)
        if self.search_mode == SearchMode.HYBRID and not (
            self.query_vector or self.text_query
        ):
            msg = "Hybrid search requires at least query_vector or text_query"
            raise ValueError(
                msg,
            )


class ModelSearchResultExplanation(BaseModel):
    """Model representing search result score explanation."""

    vector_score: float | None = Field(None, description="Vector similarity score")
    text_score: float | None = Field(None, description="Text search score")
    metadata_matches: list[str] = Field(
        default_factory=list,
        description="Matched metadata conditions",
    )
    combined_score: float = Field(..., description="Final combined score")
    ranking_factors: dict[str, float] = Field(
        default_factory=dict,
        description="Factors contributing to ranking",
    )


class ModelHybridSearchResult(BaseModel):
    """Model representing a single hybrid search result."""

    point_id: str | int = Field(..., description="Vector point identifier")
    score: float = Field(..., description="Combined similarity score")
    payload: dict[str, Any] | None = Field(
        None,
        description="Vector metadata payload",
    )
    vector: list[float] | None = Field(None, description="Vector values")
    explanation: ModelSearchResultExplanation | None = Field(
        None,
        description="Score explanation",
    )
    matched_fields: list[str] = Field(
        default_factory=list,
        description="Fields that matched the query",
    )


class ModelHybridSearchResponse(BaseModel):
    """Model representing a hybrid search response."""

    results: list[ModelHybridSearchResult] = Field(..., description="Search results")
    query_time_ms: float = Field(
        ...,
        description="Query execution time in milliseconds",
    )
    total_count: int = Field(..., description="Total number of results found")
    vector_search_time_ms: float | None = Field(
        None,
        description="Vector search time",
    )
    text_search_time_ms: float | None = Field(None, description="Text search time")
    metadata_filter_time_ms: float | None = Field(
        None,
        description="Metadata filtering time",
    )
    rerank_time_ms: float | None = Field(None, description="Reranking time")
    collection_info: dict[str, Any] = Field(
        default_factory=dict,
        description="Collection metadata",
    )
    search_query: ModelHybridSearchQuery = Field(
        ...,
        description="Original search query",
    )


class ModelSearchAggregation(BaseModel):
    """Model representing search result aggregations."""

    field: str = Field(..., description="Field to aggregate on")
    aggregation_type: Literal["count", "sum", "avg", "min", "max", "terms"] = Field(
        ...,
        description="Aggregation type",
    )
    results: dict[str, Any] = Field(..., description="Aggregation results")


class ModelAdvancedSearchQuery(BaseModel):
    """Model representing advanced search with aggregations and faceting."""

    base_query: ModelHybridSearchQuery = Field(
        ...,
        description="Base hybrid search query",
    )
    aggregations: list[ModelSearchAggregation] = Field(
        default_factory=list,
        description="Aggregations to compute",
    )
    facets: list[str] = Field(default_factory=list, description="Fields to facet on")
    group_by: str | None = Field(None, description="Field to group results by")
    sort_by: list[dict[str, str]] = Field(
        default_factory=list,
        description="Sort criteria",
    )
    explain_scores: bool = Field(
        default=False,
        description="Include detailed score explanations",
    )


class ModelAdvancedSearchResponse(BaseModel):
    """Model representing advanced search response with aggregations."""

    base_results: ModelHybridSearchResponse = Field(
        ...,
        description="Base search results",
    )
    aggregations: list[ModelSearchAggregation] = Field(
        default_factory=list,
        description="Computed aggregations",
    )
    facets: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Facet counts",
    )
    grouped_results: dict[str, list[ModelHybridSearchResult]] | None = Field(
        None,
        description="Grouped results",
    )


# Update ModelMetadataFilter to support self-referencing
ModelMetadataFilter.model_rebuild()
