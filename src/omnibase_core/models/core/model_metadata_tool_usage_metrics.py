"""
Metadata tool usage metrics model.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelMetadataToolUsageMetrics(BaseModel):
    """Usage and performance metrics for metadata tools."""

    total_invocations: int = Field(
        default=0, description="Total number of tool invocations"
    )
    success_count: int = Field(
        default=0, description="Number of successful invocations"
    )
    failure_count: int = Field(default=0, description="Number of failed invocations")
    avg_processing_time_ms: float = Field(
        default=0.0,
        description="Average processing time in milliseconds",
    )
    last_used: datetime | None = Field(default=None, description="Last usage timestamp")
    most_recent_error: str | None = Field(
        default=None,
        description="Most recent error message",
    )
    popularity_score: float = Field(
        default=0.0,
        description="Popularity score based on usage (0-100)",
    )
