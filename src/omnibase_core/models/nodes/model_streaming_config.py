"""
Streaming configuration model for REDUCER nodes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.nodes import EnumBackpressureStrategy


class ModelStreamingConfig(BaseModel):
    """Streaming configuration for REDUCER nodes."""

    model_config = ConfigDict(extra="forbid")

    buffer_size: int = Field(
        default=1000,
        description="Stream buffer size",
        ge=1,
    )
    batch_timeout_ms: int = Field(
        default=1000,
        description="Batch timeout in milliseconds",
        ge=1,
    )
    backpressure_strategy: EnumBackpressureStrategy = Field(
        default=EnumBackpressureStrategy.BUFFER,
        description="Backpressure handling strategy",
    )
    parallel_streams: int = Field(
        default=1,
        description="Number of parallel streams",
        ge=1,
    )
