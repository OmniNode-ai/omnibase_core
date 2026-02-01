"""
Metrics Summary Model for Execution Manifest.

Defines the ModelMetricsSummary model which captures optional performance
metrics for a pipeline execution.

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelMetricsSummary(BaseModel):
    """
    Optional performance metrics for pipeline execution.

    This model captures timing and resource usage metrics for the
    pipeline execution, useful for performance analysis and optimization.

    Attributes:
        total_duration_ms: Total execution duration in milliseconds
        phase_durations_ms: Duration per phase in milliseconds
        handler_durations_ms: Duration per handler in milliseconds
        peak_memory_mb: Peak memory usage in megabytes
        cpu_time_ms: CPU time consumed in milliseconds

    Example:
        >>> metrics = ModelMetricsSummary(
        ...     total_duration_ms=1234.5,
        ...     phase_durations_ms={"execute": 1000.0, "finalize": 234.5},
        ... )
        >>> metrics.total_duration_ms
        1234.5

    See Also:
        - :class:`~omnibase_core.models.manifest.model_execution_manifest.ModelExecutionManifest`:
          The parent manifest model

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    total_duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total execution duration in milliseconds",
    )

    phase_durations_ms: dict[str, float] = Field(
        default_factory=dict,
        description="Duration per phase in milliseconds (phase name -> duration)",
    )

    handler_durations_ms: dict[str, float] = Field(
        default_factory=dict,
        description="Duration per handler in milliseconds (handler ID -> duration)",
    )

    peak_memory_mb: float | None = Field(
        default=None,
        ge=0.0,
        description="Peak memory usage in megabytes",
    )

    cpu_time_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="CPU time consumed in milliseconds",
    )

    # === Utility Methods ===

    def get_total_duration_seconds(self) -> float:
        """
        Get the total duration in seconds.

        Returns:
            Total duration converted to seconds
        """
        return self.total_duration_ms / 1000.0

    def get_phase_duration(self, phase: str) -> float | None:
        """
        Get duration for a specific phase.

        Args:
            phase: Phase name to look up

        Returns:
            Duration in milliseconds or None if not found
        """
        return self.phase_durations_ms.get(phase)

    def get_handler_duration(self, handler_id: str) -> float | None:
        """
        Get duration for a specific handler.

        Args:
            handler_id: Handler ID to look up

        Returns:
            Duration in milliseconds or None if not found
        """
        return self.handler_durations_ms.get(handler_id)

    def get_slowest_phase(self) -> tuple[str, float] | None:
        """
        Get the slowest phase by duration.

        Returns:
            Tuple of (phase_name, duration_ms) or None if no phases
        """
        if not self.phase_durations_ms:
            return None
        slowest = max(self.phase_durations_ms.items(), key=lambda x: x[1])
        return slowest

    def get_slowest_handler(self) -> tuple[str, float] | None:
        """
        Get the slowest handler by duration.

        Returns:
            Tuple of (handler_id, duration_ms) or None if no handlers
        """
        if not self.handler_durations_ms:
            return None
        slowest = max(self.handler_durations_ms.items(), key=lambda x: x[1])
        return slowest

    def has_memory_metrics(self) -> bool:
        """
        Check if memory metrics are available.

        Returns:
            True if peak_memory_mb is set
        """
        return self.peak_memory_mb is not None

    def has_cpu_metrics(self) -> bool:
        """
        Check if CPU metrics are available.

        Returns:
            True if cpu_time_ms is set
        """
        return self.cpu_time_ms is not None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"MetricsSummary(total={self.total_duration_ms:.1f}ms)"

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelMetricsSummary(total_duration_ms={self.total_duration_ms!r}, "
            f"phase_count={len(self.phase_durations_ms)}, "
            f"handler_count={len(self.handler_durations_ms)})"
        )


# Export for use
__all__ = ["ModelMetricsSummary"]
