from pydantic import BaseModel, Field


class ModelPerformanceSettings(BaseModel):
    """Performance configuration settings."""

    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache time-to-live in seconds",
    )
    max_verification_time_ms: int = Field(
        default=15000,
        description="Maximum verification time in milliseconds",
    )
    parallel_verification_enabled: bool = Field(
        default=True,
        description="Whether parallel verification is enabled",
    )
    enable_caching: bool = Field(default=True, description="Whether caching is enabled")
    max_parallel_verifications: int = Field(
        default=10,
        description="Maximum parallel verifications",
    )
