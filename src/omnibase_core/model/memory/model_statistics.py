"""
Statistics model for Universal Conversation Memory System.

Provides proper Pydantic model for system statistics and metrics,
replacing ugly Dict-based StatisticsType alias with clean,
type-safe ONEX-compliant model architecture.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelToolUsage(BaseModel):
    """Tool usage statistics."""

    tool_name: str = Field(..., description="Name of the tool")
    usage_count: int = Field(..., description="Number of times tool was used")
    percentage: float = Field(..., description="Percentage of total tool usage")


class ModelTagUsage(BaseModel):
    """Tag usage statistics."""

    tag: str = Field(..., description="Tag name")
    count: int = Field(..., description="Number of times tag was used")
    percentage: float = Field(..., description="Percentage of total tag usage")


class ModelPerformanceMetrics(BaseModel):
    """Performance metrics for the memory system."""

    average_storage_time_ms: float = Field(
        default=0.0, description="Average storage operation time in milliseconds"
    )
    average_query_time_ms: float = Field(
        default=0.0, description="Average query operation time in milliseconds"
    )
    average_embedding_time_ms: float = Field(
        default=0.0, description="Average embedding generation time in milliseconds"
    )
    cache_hit_rate_percent: float = Field(
        default=0.0, description="Cache hit rate as percentage"
    )


class ModelStatistics(BaseModel):
    """
    System statistics model with proper type safety and validation.

    Replaces the ugly Dict[str, Union[...]] StatisticsType pattern with clean
    Pydantic model following ONEX architectural standards.

    Provides comprehensive system metrics and statistics with
    proper validation and type safety.
    """

    # Core metrics
    total_conversations: int = Field(
        default=0, description="Total number of conversations stored"
    )
    total_sessions: int = Field(
        default=0, description="Total number of active sessions"
    )
    total_chunks: int = Field(
        default=0, description="Total number of conversation chunks"
    )
    storage_used_bytes: int = Field(
        default=0, description="Total storage used in bytes"
    )

    # Performance metrics
    performance_metrics: Optional[ModelPerformanceMetrics] = Field(
        default=None, description="Performance metrics for system operations"
    )

    # Usage analytics
    most_used_tools: Optional[List[ModelToolUsage]] = Field(
        default=None, description="Most frequently used tools"
    )
    most_common_tags: Optional[List[ModelTagUsage]] = Field(
        default=None, description="Most commonly used tags"
    )

    # System info
    last_updated: Optional[str] = Field(
        default=None, description="ISO timestamp of last update"
    )
    provider_name: Optional[str] = Field(
        default=None, description="Vector store provider name"
    )
    system_uptime_seconds: Optional[int] = Field(
        default=None, description="System uptime in seconds"
    )

    class Config:
        """Pydantic configuration for ONEX compliance."""

        validate_assignment = True
        extra = "forbid"  # Strict validation - no extra fields allowed
