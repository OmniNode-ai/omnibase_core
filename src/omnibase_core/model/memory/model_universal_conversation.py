"""
Universal conversation memory models following ONEX standards.

Strongly typed Pydantic models for the universal conversation memory system.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ModelConversationRole(str, Enum):
    """Conversation participant roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ModelConversationContext(BaseModel):
    """Context information for a conversation interaction."""

    task_context: Optional[str] = Field(
        None, description="Current task or operation context"
    )
    tools_used: List[str] = Field(
        default_factory=list, description="Tools used in this interaction"
    )
    files_referenced: List[str] = Field(
        default_factory=list, description="Files referenced or modified"
    )
    workspace_path: Optional[str] = Field(
        None, description="Current workspace or project path"
    )
    ide_context: Optional[str] = Field(
        None, description="IDE or editor context (e.g., cursor, vscode)"
    )
    language: Optional[str] = Field(None, description="Programming language context")
    tags: List[str] = Field(default_factory=list, description="User-defined tags")


class ModelConversationMetadata(BaseModel):
    """Strongly typed metadata for conversations."""

    source_application: Optional[str] = Field(
        None, description="Application that created this conversation"
    )
    source_version: Optional[str] = Field(
        None, description="Version of the source application"
    )
    user_identifier: Optional[str] = Field(
        None, description="Anonymous user identifier"
    )
    project_identifier: Optional[str] = Field(
        None, description="Project or workspace identifier"
    )
    environment: Optional[str] = Field(
        None, description="Environment (development, production, etc.)"
    )
    custom_attributes: Optional[List["ModelCustomAttribute"]] = Field(
        None, description="Custom attributes"
    )


class ModelCustomAttribute(BaseModel):
    """Custom attribute for extensibility."""

    key: str = Field(..., description="Attribute key")
    value: str = Field(..., description="Attribute value")
    type: str = Field("string", description="Value type hint")


class ModelUniversalConversation(BaseModel):
    """Universal conversation model for cross-platform memory storage."""

    conversation_id: UUID = Field(..., description="Unique conversation identifier")
    session_id: str = Field(
        ..., description="Session identifier for grouping conversations"
    )
    interaction_timestamp: datetime = Field(
        ..., description="When the interaction occurred"
    )

    user_input: str = Field(..., description="The user's input message")
    ai_response: str = Field(..., description="The AI assistant's response")

    context: Optional[ModelConversationContext] = Field(
        None, description="Conversation context"
    )
    metadata: Optional[ModelConversationMetadata] = Field(
        None, description="Conversation metadata"
    )

    embedding_provider: Optional[str] = Field(
        None, description="Provider used for embeddings"
    )
    embedding_model: Optional[str] = Field(
        None, description="Model used for embeddings"
    )
    chunk_ids: List[str] = Field(
        default_factory=list, description="Vector chunk identifiers"
    )

    outcome: str = Field("completed", description="Interaction outcome status")
    sanitized: bool = Field(False, description="Whether sensitive data was sanitized")

    created_at: datetime = Field(
        default_factory=datetime.now, description="Record creation time"
    )
    updated_at: Optional[datetime] = Field(None, description="Last update time")


class ModelChunkMetadata(BaseModel):
    """Strongly typed metadata for conversation chunks."""

    conversation_id: UUID = Field(..., description="Parent conversation ID")
    session_id: str = Field(..., description="Session identifier")
    chunk_position: int = Field(..., description="Position in conversation")
    total_chunks: int = Field(..., description="Total chunks in conversation")
    semantic_type: str = Field(..., description="Semantic content type")
    language_detected: Optional[str] = Field(None, description="Detected language")


class ModelConversationChunk(BaseModel):
    """Represents a chunk of conversation text with embedding."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    conversation_id: UUID = Field(..., description="Parent conversation ID")
    session_id: str = Field(..., description="Session identifier")

    text: str = Field(..., description="Chunk text content")
    chunk_index: int = Field(..., description="Position in the original conversation")
    chunk_type: str = Field(..., description="Type of chunk (conversation, code, etc.)")

    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    embedding_dimensions: Optional[int] = Field(
        None, description="Embedding vector dimensions"
    )

    metadata: ModelChunkMetadata = Field(..., description="Chunk metadata")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Chunk creation time"
    )


class ModelTimeRange(BaseModel):
    """Time range for filtering."""

    start: datetime = Field(..., description="Start time")
    end: datetime = Field(..., description="End time")


class ModelContextFilter(BaseModel):
    """Context-based filtering criteria."""

    tools_used: Optional[List[str]] = Field(None, description="Filter by tools")
    languages: Optional[List[str]] = Field(
        None, description="Filter by programming languages"
    )
    ide_contexts: Optional[List[str]] = Field(None, description="Filter by IDE/editor")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")


class ModelConversationQuery(BaseModel):
    """Query parameters for conversation search."""

    query: str = Field(..., description="Search query text")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    session_filter: Optional[str] = Field(None, description="Filter by session ID")
    similarity_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum similarity score"
    )

    timeframe: Optional[ModelTimeRange] = Field(None, description="Time range filter")
    context_filter: Optional[ModelContextFilter] = Field(
        None, description="Context-based filters"
    )

    include_metadata: bool = Field(True, description="Include full metadata in results")
    include_embeddings: bool = Field(
        False, description="Include embedding vectors in results"
    )


class ModelConversationResult(BaseModel):
    """Search result for conversation queries."""

    conversation: ModelUniversalConversation = Field(
        ..., description="Matched conversation"
    )
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Similarity/relevance score"
    )
    matched_chunks: List[ModelConversationChunk] = Field(
        default_factory=list, description="Matching chunks"
    )

    highlight_snippets: Optional[List[str]] = Field(
        None, description="Highlighted matching text"
    )
    context_summary: Optional[str] = Field(
        None, description="AI-generated context summary"
    )


class ModelProviderHealth(str, Enum):
    """Provider health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ModelProviderMetrics(BaseModel):
    """Performance metrics for a provider."""

    embedding_latency_ms: float = Field(..., description="Average embedding latency")
    query_latency_ms: float = Field(..., description="Average query latency")
    storage_latency_ms: float = Field(..., description="Average storage latency")

    success_rate_percent: float = Field(..., description="Success rate percentage")
    error_rate_percent: float = Field(..., description="Error rate percentage")

    requests_per_minute: float = Field(..., description="Current request rate")
    embeddings_generated: int = Field(..., description="Total embeddings generated")
    queries_processed: int = Field(..., description="Total queries processed")


class ModelProviderStatus(BaseModel):
    """Health and status information for memory provider."""

    provider_name: str = Field(..., description="Provider identifier")
    health: ModelProviderHealth = Field(..., description="Overall health status")

    embedding_service_healthy: bool = Field(..., description="Embedding service status")
    vector_store_healthy: bool = Field(..., description="Vector store status")
    api_service_healthy: bool = Field(..., description="API service status")

    total_conversations: int = Field(0, description="Total stored conversations")
    total_chunks: int = Field(0, description="Total stored chunks")
    storage_used_bytes: int = Field(0, description="Storage space used")

    metrics: Optional[ModelProviderMetrics] = Field(
        None, description="Performance metrics"
    )

    last_health_check: datetime = Field(
        default_factory=datetime.now, description="Last check time"
    )
    uptime_seconds: Optional[int] = Field(None, description="Service uptime")

    active_providers: List[str] = Field(
        default_factory=list, description="Active embedding providers"
    )
    failed_providers: List[str] = Field(
        default_factory=list, description="Failed providers"
    )


class ModelMemoryExportFormat(str, Enum):
    """Supported export formats."""

    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    MARKDOWN = "markdown"


class ModelToolUsageStats(BaseModel):
    """Statistics for tool usage."""

    tool_name: str = Field(..., description="Tool identifier")
    usage_count: int = Field(..., description="Number of times used")
    last_used: datetime = Field(..., description="Last usage timestamp")


class ModelTagFrequency(BaseModel):
    """Tag frequency statistics."""

    tag: str = Field(..., description="Tag value")
    count: int = Field(..., description="Usage count")
    percentage: float = Field(..., description="Percentage of total")


class ModelDailyStats(BaseModel):
    """Daily conversation statistics."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    conversation_count: int = Field(..., description="Conversations on this date")
    unique_sessions: int = Field(..., description="Unique sessions on this date")
    average_length: float = Field(..., description="Average conversation length")


class ModelPerformanceStats(BaseModel):
    """System performance statistics."""

    average_storage_time_ms: float = Field(
        ..., description="Avg time to store conversation"
    )
    average_query_time_ms: float = Field(..., description="Avg query response time")
    average_embedding_time_ms: float = Field(
        ..., description="Avg embedding generation time"
    )

    cache_hit_rate_percent: float = Field(..., description="Cache hit rate")
    compression_ratio: float = Field(..., description="Storage compression ratio")


class ModelMemoryStatistics(BaseModel):
    """Statistics about the memory system."""

    total_conversations: int = Field(..., description="Total conversation count")
    total_sessions: int = Field(..., description="Unique session count")
    total_chunks: int = Field(..., description="Total chunk count")

    storage_used_bytes: int = Field(..., description="Total storage used")
    index_size_bytes: int = Field(..., description="Vector index size")

    average_conversation_length: float = Field(
        ..., description="Avg conversation length"
    )
    average_chunks_per_conversation: float = Field(
        ..., description="Avg chunks per conversation"
    )

    most_used_tools: List[ModelToolUsageStats] = Field(
        default_factory=list, description="Tool usage stats"
    )
    most_common_tags: List[ModelTagFrequency] = Field(
        default_factory=list, description="Tag frequency"
    )

    daily_stats: List[ModelDailyStats] = Field(
        default_factory=list, description="Daily statistics"
    )
    performance: Optional[ModelPerformanceStats] = Field(
        None, description="Performance metrics"
    )

    last_updated: datetime = Field(
        default_factory=datetime.now, description="Stats update time"
    )
