"""
Typed custom metrics model for introspection additional info.

This module provides strongly-typed metrics for introspection patterns.
"""

from pydantic import BaseModel, Field


class ModelIntrospectionCustomMetrics(BaseModel):
    """
    Typed custom metrics for introspection additional info.

    Replaces dict[str, Any] custom_metrics field in ModelIntrospectionAdditionalInfo
    with explicit typed fields for introspection metrics.
    """

    request_count: int | None = Field(
        default=None,
        description="Total request count",
        ge=0,
    )
    error_count: int | None = Field(
        default=None,
        description="Total error count",
        ge=0,
    )
    average_latency_ms: float | None = Field(
        default=None,
        description="Average latency in milliseconds",
        ge=0.0,
    )
    p99_latency_ms: float | None = Field(
        default=None,
        description="99th percentile latency in milliseconds",
        ge=0.0,
    )
    throughput_per_second: float | None = Field(
        default=None,
        description="Throughput in requests per second",
        ge=0.0,
    )
    cache_size: int | None = Field(
        default=None,
        description="Current cache size",
        ge=0,
    )
    custom_values: dict[str, float] = Field(
        default_factory=dict,
        description="Additional custom numeric metrics",
    )


__all__ = ["ModelIntrospectionCustomMetrics"]
