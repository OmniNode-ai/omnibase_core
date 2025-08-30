"""ModelPerformanceHints: Performance optimization hints for high-throughput processing"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelPerformanceHints(BaseModel):
    """Performance optimization hints for high-throughput processing"""

    batch_size_hint: Optional[int] = Field(
        None, description="Suggested batch size for efficient processing"
    )
    processing_timeout_ms: Optional[int] = Field(
        None, description="Maximum processing time before timeout"
    )
    memory_footprint_bytes: Optional[int] = Field(
        None, description="Estimated memory usage for resource planning"
    )
