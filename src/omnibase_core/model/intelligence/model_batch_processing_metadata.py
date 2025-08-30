"""
Batch processing metadata model - Strongly typed batch metadata structure.

Replaces Dict[str, Any] usage with strongly typed batch processing information.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelBatchProcessingMetadata(BaseModel):
    """Strongly typed batch processing metadata."""

    batch_id: str = Field(description="Unique batch identifier")
    batch_size: int = Field(description="Number of items in batch")
    processing_mode: str = Field(description="Batch processing mode")
    priority_level: str = Field(description="Batch priority level")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    timeout_seconds: int = Field(default=300, description="Processing timeout")
    checkpoint_interval: int | None = Field(
        default=None,
        description="Checkpoint interval in seconds",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Batch dependency identifiers",
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Scheduled processing time",
    )
