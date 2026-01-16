"""
Summary statistics model for trace aggregation.

Defines ModelTraceSummary containing aggregate metrics across a set of traces,
including counts, success rates, and duration percentiles. Returned by
ProtocolTraceStore.summary() method.

Example:
    >>> from omnibase_core.models.trace_query.model_trace_summary import ModelTraceSummary
    >>> from datetime import datetime, UTC
    >>>
    >>> summary = ModelTraceSummary(
    ...     time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
    ...     time_range_end=datetime(2024, 1, 2, tzinfo=UTC),
    ...     total_traces=100,
    ...     success_count=85,
    ...     failure_count=10,
    ...     partial_count=5,
    ...     success_rate=0.85,
    ...     avg_duration_ms=150.0,
    ...     p50_duration_ms=120.0,
    ...     p95_duration_ms=400.0,
    ...     p99_duration_ms=750.0,
    ... )
    >>> print(f"Success rate: {summary.success_rate:.1%}")
    Success rate: 85.0%

See Also:
    - :class:`~omnibase_core.protocols.storage.protocol_trace_store.ProtocolTraceStore`:
      Protocol that returns this summary model
    - :class:`~omnibase_core.models.trace_query.model_trace_query.ModelTraceQuery`:
      Query filters for scoping the summary

.. versionadded:: 0.4.0
    Added as part of Trace Recording Service (OMN-1209)
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelTraceSummary(BaseModel):
    """
    Aggregate statistics for a set of execution traces.

    Provides counts, success metrics, and duration percentiles across all
    traces matching the query filters. Used for monitoring, dashboards,
    and SLA tracking.

    Attributes:
        time_range_start: Start of the time range covered by this summary.
        time_range_end: End of the time range covered by this summary.
        total_traces: Total number of traces in the summary.
        success_count: Number of traces with SUCCESS or COMPLETED status.
        failure_count: Number of traces with FAILED or TIMEOUT status.
        partial_count: Number of traces with PARTIAL status.
        success_rate: Ratio of successful traces (0.0 to 1.0).
        avg_duration_ms: Average execution duration in milliseconds.
        p50_duration_ms: Median (50th percentile) duration in milliseconds.
        p95_duration_ms: 95th percentile duration in milliseconds.
        p99_duration_ms: 99th percentile duration in milliseconds.

    Example:
        >>> summary = await store.summary(query)
        >>> print(f"Total traces: {summary.total_traces}")
        >>> print(f"Success rate: {summary.success_rate:.1%}")
        >>> print(f"P95 latency: {summary.p95_duration_ms:.1f}ms")
        >>>
        >>> if summary.success_rate < 0.95:
        ...     print("WARNING: Success rate below SLA threshold!")

    .. versionadded:: 0.4.0
        Added as part of Trace Recording Service (OMN-1209)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # === Time Range ===

    time_range_start: datetime = Field(
        ...,
        description="Start of the time range covered by this summary",
    )

    time_range_end: datetime = Field(
        ...,
        description="End of the time range covered by this summary",
    )

    # === Counts ===

    total_traces: int = Field(
        ...,
        ge=0,
        description="Total number of traces in the summary",
    )

    success_count: int = Field(
        ...,
        ge=0,
        description="Number of traces with SUCCESS or COMPLETED status",
    )

    failure_count: int = Field(
        ...,
        ge=0,
        description="Number of traces with FAILED or TIMEOUT status",
    )

    partial_count: int = Field(
        ...,
        ge=0,
        description="Number of traces with PARTIAL status",
    )

    # === Rates ===

    success_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ratio of successful traces (0.0 to 1.0)",
    )

    # === Duration Metrics ===

    avg_duration_ms: float = Field(
        ...,
        ge=0.0,
        description="Average execution duration in milliseconds",
    )

    p50_duration_ms: float = Field(
        ...,
        ge=0.0,
        description="Median (50th percentile) duration in milliseconds",
    )

    p95_duration_ms: float = Field(
        ...,
        ge=0.0,
        description="95th percentile duration in milliseconds",
    )

    p99_duration_ms: float = Field(
        ...,
        ge=0.0,
        description="99th percentile duration in milliseconds",
    )

    # === Validators ===

    @model_validator(mode="after")
    def validate_time_ordering(self) -> "ModelTraceSummary":
        """Validate that time_range_end is not before time_range_start."""
        if self.time_range_end < self.time_range_start:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"time_range_end ({self.time_range_end}) cannot be before "
                f"time_range_start ({self.time_range_start})"
            )
        return self

    @model_validator(mode="after")
    def validate_counts_consistency(self) -> "ModelTraceSummary":
        """Validate that status counts don't exceed total."""
        counted = self.success_count + self.failure_count + self.partial_count
        if counted > self.total_traces:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"Sum of status counts ({counted}) exceeds total_traces "
                f"({self.total_traces})"
            )
        return self

    @model_validator(mode="after")
    def validate_percentile_ordering(self) -> "ModelTraceSummary":
        """Validate that percentiles are in ascending order."""
        if self.p50_duration_ms > self.p95_duration_ms:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"p50_duration_ms ({self.p50_duration_ms}) cannot exceed "
                f"p95_duration_ms ({self.p95_duration_ms})"
            )
        if self.p95_duration_ms > self.p99_duration_ms:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"p95_duration_ms ({self.p95_duration_ms}) cannot exceed "
                f"p99_duration_ms ({self.p99_duration_ms})"
            )
        return self

    # === Utility Methods ===

    def get_other_count(self) -> int:
        """
        Get count of traces with status other than SUCCESS/FAILED/PARTIAL.

        This includes CANCELLED, SKIPPED, RUNNING, PENDING, etc.

        Returns:
            Number of traces with other statuses.
        """
        return self.total_traces - (
            self.success_count + self.failure_count + self.partial_count
        )

    def get_failure_rate(self) -> float:
        """
        Get the failure rate (ratio of failed traces).

        Returns:
            Ratio of failed traces (0.0 to 1.0), or 0.0 if no traces.
        """
        if self.total_traces == 0:
            return 0.0
        return self.failure_count / self.total_traces

    def get_partial_rate(self) -> float:
        """
        Get the partial success rate (ratio of partial traces).

        Returns:
            Ratio of partial traces (0.0 to 1.0), or 0.0 if no traces.
        """
        if self.total_traces == 0:
            return 0.0
        return self.partial_count / self.total_traces

    def is_empty(self) -> bool:
        """
        Check if the summary contains no traces.

        Returns:
            True if total_traces is 0.
        """
        return self.total_traces == 0

    def meets_sla(self, min_success_rate: float, max_p99_ms: float) -> bool:
        """
        Check if traces meet SLA thresholds.

        Args:
            min_success_rate: Minimum required success rate (0.0 to 1.0).
            max_p99_ms: Maximum allowed P99 latency in milliseconds.

        Returns:
            True if both SLA thresholds are met.

        Example:
            >>> if summary.meets_sla(min_success_rate=0.99, max_p99_ms=500.0):
            ...     print("SLA met!")
            ... else:
            ...     print("SLA violated!")
        """
        return (
            self.success_rate >= min_success_rate and self.p99_duration_ms <= max_p99_ms
        )

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"TraceSummary({self.total_traces} traces, "
            f"{self.success_rate:.1%} success, "
            f"p50={self.p50_duration_ms:.1f}ms, "
            f"p95={self.p95_duration_ms:.1f}ms, "
            f"p99={self.p99_duration_ms:.1f}ms)"
        )


__all__ = ["ModelTraceSummary"]
