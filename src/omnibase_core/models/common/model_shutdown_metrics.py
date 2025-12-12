"""
Typed metrics model for node shutdown events.

This module provides strongly-typed metrics for shutdown patterns.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelShutdownMetrics(BaseModel):
    """
    Typed metrics for node shutdown events.

    Replaces dict[str, Any] final_metrics field in ModelNodeShutdownEvent
    with explicit typed fields for shutdown metrics.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if shutdown was due to error",
    )
    maintenance_reason: str | None = Field(
        default=None,
        description="Reason for maintenance shutdown",
    )
    force_reason: str | None = Field(
        default=None,
        description="Reason for forced shutdown",
    )
    total_requests: int | None = Field(
        default=None,
        description="Total requests processed during lifetime",
        ge=0,
    )
    total_errors: int | None = Field(
        default=None,
        description="Total errors encountered during lifetime",
        ge=0,
    )
    average_response_time_ms: float | None = Field(
        default=None,
        description="Average response time in milliseconds",
        ge=0.0,
    )
    peak_memory_mb: int | None = Field(
        default=None,
        description="Peak memory usage in megabytes",
        ge=0,
    )
    cpu_time_seconds: float | None = Field(
        default=None,
        description="Total CPU time consumed in seconds",
        ge=0.0,
    )


__all__ = ["ModelShutdownMetrics"]
