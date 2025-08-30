"""ModelPerformanceHints: Performance optimization hints for high-throughput processing"""

from pydantic import BaseModel, Field


class ModelPerformanceHints(BaseModel):
    """Performance optimization hints for high-throughput processing"""

    batch_size_hint: int | None = Field(
        None,
        description="Suggested batch size for efficient processing",
    )
    processing_timeout_ms: int | None = Field(
        None,
        description="Maximum processing time before timeout",
    )
    memory_footprint_bytes: int | None = Field(
        None,
        description="Estimated memory usage for resource planning",
    )
