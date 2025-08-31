"""
Qdrant health status model for database monitoring.

This model represents the health status and metrics of a Qdrant instance,
following ONEX canonical patterns with proper validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field


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
