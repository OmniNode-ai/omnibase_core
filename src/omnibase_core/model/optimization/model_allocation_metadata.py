"""
Model for allocation metadata.

Metadata for quota allocation tracking.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelAllocationMetadata(BaseModel):
    """Metadata for quota allocation."""

    last_optimization: datetime | None = Field(
        None,
        description="Last optimization timestamp",
    )
    optimization_count: int = Field(0, description="Number of optimizations")
    peak_usage: int = Field(0, description="Peak token usage")
    average_task_tokens: int = Field(0, description="Average tokens per task")
