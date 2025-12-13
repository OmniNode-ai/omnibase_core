"""
Latency profile assessment model to replace Dict[str, Any] usage.
"""

from pydantic import BaseModel, Field


class ModelLatencyProfile(BaseModel):
    """
    Latency profile assessment with typed fields.
    Replaces Dict[str, Any] for _get_latency_profile() returns.
    """

    # Latency assessments
    connection_latency: str = Field(
        default=...,
        description="Connection latency level (low/medium/high)",
    )
    query_latency: str = Field(
        default=..., description="Query latency level (low/medium/high)"
    )
    overall_latency: str = Field(default=..., description="Overall latency assessment")

    # Latency factors
    factors: list[str] = Field(
        default_factory=list,
        description="Factors affecting latency",
    )

    # Specific measurements
    avg_connection_time_ms: float | None = Field(
        default=None,
        description="Average connection time",
    )
    avg_query_time_ms: float | None = Field(
        default=None, description="Average query time"
    )
    p95_connection_time_ms: float | None = Field(
        default=None,
        description="95th percentile connection time",
    )
    p95_query_time_ms: float | None = Field(
        default=None,
        description="95th percentile query time",
    )

    # Recommendations
    optimization_suggestions: list[str] = Field(
        default_factory=list,
        description="Latency optimization suggestions",
    )

    # Driver-specific latency
    driver_latency: str | None = Field(
        default=None,
        description="Driver-specific latency characteristics",
    )
