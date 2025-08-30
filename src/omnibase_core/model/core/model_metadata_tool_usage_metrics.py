"""
Metadata tool usage metrics model.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelMetadataToolUsageMetrics(BaseModel):
    """Usage and performance metrics for metadata tools."""

    total_invocations: int = Field(0, description="Total number of tool invocations")
    success_count: int = Field(0, description="Number of successful invocations")
    failure_count: int = Field(0, description="Number of failed invocations")
    avg_processing_time_ms: float = Field(
        0.0, description="Average processing time in milliseconds"
    )
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    most_recent_error: Optional[str] = Field(
        None, description="Most recent error message"
    )
    popularity_score: float = Field(
        0.0, description="Popularity score based on usage (0-100)"
    )
