"""
Typed custom metrics model for health monitoring.

This module provides strongly-typed metrics for health monitoring patterns.
"""

from pydantic import BaseModel, Field


class ModelCustomHealthMetrics(BaseModel):
    """
    Typed custom metrics for health monitoring.

    Replaces dict[str, Any] custom_metrics field in ModelHealthMetrics
    with explicit typed fields for custom health metrics.
    """

    status: str | None = Field(
        default=None,
        description="Health status (healthy, warning, critical, error)",
    )
    status_code: float | None = Field(
        default=None,
        description="Numeric status code (1.0=healthy, 0.5=warning, 0.0=critical)",
    )
    queue_depth: int | None = Field(
        default=None,
        description="Current queue depth",
        ge=0,
    )
    cache_hit_rate: float | None = Field(
        default=None,
        description="Cache hit rate (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    thread_count: int | None = Field(
        default=None,
        description="Current thread count",
        ge=0,
    )
    open_connections: int | None = Field(
        default=None,
        description="Number of open connections",
        ge=0,
    )
    disk_usage_percent: float | None = Field(
        default=None,
        description="Disk usage percentage",
        ge=0.0,
        le=100.0,
    )
    network_io_bytes: int | None = Field(
        default=None,
        description="Network I/O in bytes",
        ge=0,
    )
    custom_values: dict[str, float] = Field(
        default_factory=dict,
        description="Additional custom numeric metrics",
    )


__all__ = ["ModelCustomHealthMetrics"]
