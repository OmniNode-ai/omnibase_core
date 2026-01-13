"""
Streaming Configuration Model.

Streaming configuration for large datasets in NodeReducer implementations.
Defines streaming parameters, buffer management, and memory-efficient processing
for large data volumes.

Part of the "one model per file" convention for clean architecture.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelStreamingConfig(BaseModel):
    """
    Streaming configuration for large datasets.

    Defines streaming parameters, buffer management,
    and memory-efficient processing for large data volumes.
    """

    enabled: bool = Field(default=True, description="Enable streaming processing")

    buffer_size: int = Field(
        default=8192,
        description="Stream buffer size in bytes",
        ge=1024,
    )

    window_size: int = Field(
        default=1000,
        description="Processing window size for streaming operations",
        ge=1,
    )

    memory_threshold_mb: int = Field(
        default=512,
        description="Memory threshold for streaming activation in MB",
        ge=1,
    )

    backpressure_enabled: bool = Field(
        default=True,
        description="Enable backpressure handling for streaming",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
