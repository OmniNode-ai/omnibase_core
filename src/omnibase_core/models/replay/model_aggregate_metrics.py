"""
ModelAggregateMetrics - Aggregate metrics from corpus replay.

This module provides the ModelAggregateMetrics model for capturing
aggregate timing and statistical metrics from replaying a corpus,
including averages, percentiles, and distribution data.

Thread Safety:
    ModelAggregateMetrics is frozen (immutable) after creation, making it
    safe to share across threads.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelAggregateMetrics

        metrics = ModelAggregateMetrics(
            total_duration_ms=5000.0,
            avg_duration_ms=100.0,
            min_duration_ms=50.0,
            max_duration_ms=250.0,
            p50_duration_ms=95.0,
            p95_duration_ms=200.0,
            p99_duration_ms=245.0,
        )
        print(f"P95: {metrics.p95_duration_ms:.1f}ms")

Related:
    - OMN-1204: Corpus Replay Orchestrator
    - ModelCorpusReplayResult: Contains these aggregate metrics

.. versionadded:: 0.6.0
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelAggregateMetrics(BaseModel):
    """
    Aggregate timing and statistical metrics from corpus replay.

    Provides summary statistics including total, average, min/max,
    and percentile durations for performance analysis and comparison.

    Attributes:
        total_duration_ms: Total wall-clock time for all replays.
        avg_duration_ms: Average replay duration.
        min_duration_ms: Minimum replay duration.
        max_duration_ms: Maximum replay duration.
        p50_duration_ms: 50th percentile (median) duration.
        p95_duration_ms: 95th percentile duration.
        p99_duration_ms: 99th percentile duration.
        std_dev_ms: Standard deviation of durations.
        success_rate: Fraction of successful replays (0.0 to 1.0).
        throughput_per_sec: Replays completed per second.

    Thread Safety:
        This model is frozen (immutable) after creation, making it safe
        to share across threads.

    Example:
        >>> metrics = ModelAggregateMetrics(
        ...     total_duration_ms=5000.0,
        ...     avg_duration_ms=100.0,
        ...     min_duration_ms=50.0,
        ...     max_duration_ms=250.0,
        ... )
        >>> metrics.avg_duration_ms
        100.0

    .. versionadded:: 0.6.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    total_duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total wall-clock time for all replays in milliseconds",
    )

    avg_duration_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Average replay duration in milliseconds",
    )

    min_duration_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Minimum replay duration in milliseconds",
    )

    max_duration_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Maximum replay duration in milliseconds",
    )

    p50_duration_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="50th percentile (median) duration in milliseconds",
    )

    p95_duration_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="95th percentile duration in milliseconds",
    )

    p99_duration_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="99th percentile duration in milliseconds",
    )

    std_dev_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Standard deviation of durations in milliseconds",
    )

    success_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of successful replays (0.0 to 1.0)",
    )

    throughput_per_sec: float | None = Field(
        default=None,
        ge=0.0,
        description="Replays completed per second",
    )

    @classmethod
    def from_durations(
        cls,
        durations: list[float],
        total_duration_ms: float,
        success_count: int,
        total_count: int,
    ) -> ModelAggregateMetrics:
        """Create metrics from a list of durations.

        Args:
            durations: List of individual replay durations in milliseconds.
            total_duration_ms: Total wall-clock time for the replay.
            success_count: Number of successful replays.
            total_count: Total number of replay attempts.

        Returns:
            ModelAggregateMetrics with computed statistics.
        """
        if not durations:
            return cls(
                total_duration_ms=total_duration_ms,
                success_rate=1.0 if total_count == 0 else 0.0,
            )

        sorted_durations = sorted(durations)
        n = len(sorted_durations)

        # Calculate percentiles using linear interpolation
        def percentile(p: float) -> float:
            # Handle single-element list: all percentiles equal that element
            if n == 1:
                return sorted_durations[0]
            k = (n - 1) * p
            f = int(k)
            c = f + 1 if f + 1 < n else f
            return sorted_durations[f] + (k - f) * (
                sorted_durations[c] - sorted_durations[f]
            )

        avg = sum(durations) / n
        variance = sum((d - avg) ** 2 for d in durations) / n
        std_dev = variance**0.5

        success_rate = success_count / total_count if total_count > 0 else 0.0
        throughput = (n * 1000.0 / total_duration_ms) if total_duration_ms > 0 else None

        return cls(
            total_duration_ms=total_duration_ms,
            avg_duration_ms=avg,
            min_duration_ms=sorted_durations[0],
            max_duration_ms=sorted_durations[-1],
            p50_duration_ms=percentile(0.50),
            p95_duration_ms=percentile(0.95),
            p99_duration_ms=percentile(0.99),
            std_dev_ms=std_dev,
            success_rate=success_rate,
            throughput_per_sec=throughput,
        )

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        parts = [f"total={self.total_duration_ms:.1f}ms"]
        if self.avg_duration_ms is not None:
            parts.append(f"avg={self.avg_duration_ms:.1f}ms")
        if self.p95_duration_ms is not None:
            parts.append(f"p95={self.p95_duration_ms:.1f}ms")
        parts.append(f"success={self.success_rate:.1%}")
        return f"AggregateMetrics({', '.join(parts)})"


__all__ = ["ModelAggregateMetrics"]
