"""
Performance profile model to replace Dict[str, Any] usage for performance data.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from .model_performance_benchmark import ModelPerformanceBenchmark


class ModelPerformanceProfile(BaseModel):
    """
    Performance profile with typed fields.
    Replaces Dict[str, Any] for get_performance_profile() returns.
    """

    # Overall performance
    overall_score: float | None = Field(
        None,
        description="Overall performance score (0-100)",
        ge=0,
        le=100,
    )
    performance_tier: str | None = Field(
        None,
        description="Performance tier classification",
    )

    # Latency metrics
    avg_latency_ms: float | None = Field(
        None,
        description="Average latency in milliseconds",
        ge=0,
    )
    p50_latency_ms: float | None = Field(
        None,
        description="50th percentile latency",
        ge=0,
    )
    p95_latency_ms: float | None = Field(
        None,
        description="95th percentile latency",
        ge=0,
    )
    p99_latency_ms: float | None = Field(
        None,
        description="99th percentile latency",
        ge=0,
    )
    max_latency_ms: float | None = Field(
        None,
        description="Maximum observed latency",
        ge=0,
    )

    # Throughput metrics
    avg_throughput_rps: float | None = Field(
        None,
        description="Average throughput (requests/second)",
        ge=0,
    )
    peak_throughput_rps: float | None = Field(
        None,
        description="Peak throughput",
        ge=0,
    )
    sustained_throughput_rps: float | None = Field(
        None,
        description="Sustained throughput",
        ge=0,
    )

    # Resource efficiency (0-100 percentages)
    cpu_efficiency: float | None = Field(
        None,
        description="CPU efficiency ratio",
        ge=0,
        le=100,
    )
    memory_efficiency: float | None = Field(
        None,
        description="Memory efficiency ratio",
        ge=0,
        le=100,
    )
    io_efficiency: float | None = Field(
        None,
        description="I/O efficiency ratio",
        ge=0,
        le=100,
    )

    # Scalability metrics
    linear_scalability_factor: float | None = Field(
        None,
        description="Linear scalability factor",
        ge=0,
    )
    max_concurrent_operations: int | None = Field(
        None,
        description="Maximum concurrent operations",
        ge=0,
    )
    saturation_point: int | None = Field(
        None,
        description="Load at which performance degrades",
        ge=0,
    )

    # Operation benchmarks - properly typed list
    operation_benchmarks: list[ModelPerformanceBenchmark] = Field(
        default_factory=list,
        description="Detailed benchmarks per operation",
    )

    # Bottlenecks and optimization opportunities - properly typed lists
    identified_bottlenecks: list[str] = Field(
        default_factory=list,
        description="Identified performance bottlenecks",
    )
    optimization_recommendations: list[str] = Field(
        default_factory=list,
        description="Recommended optimizations",
    )

    # Comparison metrics - better typed than Dict[str, Any]
    baseline_comparison_score: float | None = Field(
        None,
        description="Performance score compared to baseline",
        ge=0,
    )
    previous_version_comparison_score: float | None = Field(
        None,
        description="Performance score compared to previous version",
        ge=0,
    )

    # Profile metadata
    profile_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When profile was generated",
    )
    profile_duration_seconds: int | None = Field(
        None,
        description="Duration of profiling session",
        ge=0,
    )
    environment: str | None = Field(
        None,
        description="Environment where profiling was done",
    )
    load_pattern: str | None = Field(
        None,
        description="Load pattern used for profiling",
    )

    model_config = ConfigDict()

    # ONEX Phase 3C: Factory method eliminated - use direct instantiation
    # Old pattern: ModelPerformanceProfile.from_dict(data)
    # New pattern: ModelPerformanceProfile(**data)

    @field_serializer("profile_timestamp")
    def serialize_datetime(self, value: datetime) -> str:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return str(value) if value else ""


# Compatibility alias
PerformanceProfile = ModelPerformanceProfile
