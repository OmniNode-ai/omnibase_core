"""
Performance configuration model for contract content.

Provides strongly typed performance configuration specifications.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelPerformanceConfig(BaseModel):
    """Performance configuration for node contracts."""

    model_config = ConfigDict(extra="forbid")

    timeout_ms: int | None = Field(
        None,
        description="Operation timeout in milliseconds",
        ge=0,
    )
    memory_limit_mb: int | None = Field(
        None,
        description="Memory limit in megabytes",
        ge=0,
    )
    cpu_limit_cores: float | None = Field(
        None,
        description="CPU limit in cores",
        ge=0,
    )
    max_concurrent_operations: int | None = Field(
        None,
        description="Maximum concurrent operations",
        ge=1,
    )
    batch_size: int | None = Field(
        None,
        description="Batch size for batch operations",
        ge=1,
    )
    cache_ttl_seconds: int | None = Field(
        None,
        description="Cache TTL in seconds",
        ge=0,
    )
    retry_attempts: int | None = Field(
        None,
        description="Number of retry attempts",
        ge=0,
    )
    backoff_multiplier: float | None = Field(
        None,
        description="Backoff multiplier for retries",
        ge=1.0,
    )
