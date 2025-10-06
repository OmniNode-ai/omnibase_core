from pydantic import BaseModel, Field


class ModelVerificationMetrics(BaseModel):
    """Verification performance metrics."""

    total_verifications: int = Field(
        default=0,
        description="Total number of verifications performed",
    )
    cache_hit_rate: float = Field(default=0.0, description="Cache hit rate percentage")
    average_verification_time_ms: float = Field(
        default=0.0,
        description="Average verification time in milliseconds",
    )
    fastest_verification_ms: float = Field(
        default=0.0,
        description="Fastest verification time in milliseconds",
    )
    slowest_verification_ms: float = Field(
        default=0.0,
        description="Slowest verification time in milliseconds",
    )
