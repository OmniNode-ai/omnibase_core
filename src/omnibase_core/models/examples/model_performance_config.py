from pydantic import BaseModel, Field


class ModelPerformanceConfig(BaseModel):
    """Performance configuration model."""

    cache_max_size: int = Field(default=1000, description="Maximum cache entries")
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL in seconds")
    max_concurrent_operations: int = Field(
        default=100, description="Maximum concurrent operations"
    )
    error_rate_threshold: float = Field(
        default=0.1, description="Error rate threshold for health"
    )
    min_operations_for_health: int = Field(
        default=10, description="Min operations before health evaluation"
    )
    health_score_threshold_good: float = Field(
        default=0.6, description="Health score threshold for good status"
    )
