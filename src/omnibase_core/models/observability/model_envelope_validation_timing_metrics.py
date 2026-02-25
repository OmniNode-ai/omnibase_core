# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Envelope Validation Timing Metrics Model.

Immutable model capturing latency statistics for envelope validation operations.
Supports p50/p95/p99 percentile estimation via histogram buckets and provides
per-step timing breakdown for structured observability.

Design Pattern:
    Follows the same immutable accumulator pattern as ``ModelDispatchMetrics``
    and ``ModelHandlerMetrics``. Call ``record_validation()`` to produce an
    updated instance; the original is never mutated.

Thread Safety:
    All instances are frozen (immutable). Thread-safe to share across threads;
    callers must synchronise the accumulation loop externally.

Example:
    >>> from omnibase_core.models.observability import ModelEnvelopeValidationTimingMetrics
    >>>
    >>> metrics = ModelEnvelopeValidationTimingMetrics()
    >>> metrics = metrics.record_validation(
    ...     total_duration_ms=2.3,
    ...     step_durations_ms={
    ...         "envelope_structure": 0.8,
    ...         "correlation_id": 0.5,
    ...         "payload_presence": 0.3,
    ...     },
    ...     passed=True,
    ... )
    >>> print(f"p95 estimate: {metrics.p95_duration_ms:.1f} ms")

See Also:
    - ``ModelEnvelopeValidationFailureMetrics``: Companion failure-rate model
    - ``ModelEnvelopeValidationSummary``: Combined timing + failure summary
    - ``ModelDispatchMetrics``: Dispatch-level timing reference implementation

.. versionadded:: 0.6.0
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

# Histogram bucket boundaries in milliseconds — aligned with Prometheus defaults
VALIDATION_LATENCY_HISTOGRAM_BUCKETS: tuple[float, ...] = (
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    25.0,
    50.0,
    100.0,
)


class ModelEnvelopeValidationTimingMetrics(BaseModel):
    """Immutable timing metrics for envelope validation operations.

    Accumulates latency observations across all validation checks performed
    before dispatch. Provides histogram buckets sufficient for p50/p95/p99
    estimation and per-step duration breakdowns.

    Attributes:
        total_validations: Number of validation operations recorded.
        passed_validations: Number of validation operations that passed.
        failed_validations: Number of validation operations that failed.
        total_duration_ms: Cumulative validation latency in milliseconds.
        min_duration_ms: Minimum observed validation latency.
        max_duration_ms: Maximum observed validation latency.
        latency_histogram: Histogram buckets for latency distribution.
        step_totals_ms: Cumulative latency per named validation step.
        step_counts: Number of observations per named validation step.
        last_recorded_at: Timestamp of the most recent observation.

    Example:
        >>> metrics = ModelEnvelopeValidationTimingMetrics()
        >>> metrics = metrics.record_validation(
        ...     total_duration_ms=1.5,
        ...     step_durations_ms={"envelope_structure": 0.8},
        ...     passed=True,
        ... )
        >>> metrics.avg_duration_ms
        1.5
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # ---- Counts ----
    total_validations: int = Field(
        default=0,
        ge=0,
        description="Total number of validation operations recorded.",
    )
    passed_validations: int = Field(
        default=0,
        ge=0,
        description="Number of validation operations that passed.",
    )
    failed_validations: int = Field(
        default=0,
        ge=0,
        description="Number of validation operations that failed.",
    )

    # ---- Latency Statistics ----
    total_duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Cumulative validation latency in milliseconds.",
    )
    min_duration_ms: float | None = Field(
        default=None,
        description="Minimum observed validation latency in milliseconds.",
    )
    max_duration_ms: float | None = Field(
        default=None,
        description="Maximum observed validation latency in milliseconds.",
    )

    # ---- Latency Histogram ----
    latency_histogram: dict[str, int] = Field(
        default_factory=lambda: {
            "le_0_1ms": 0,
            "le_0_25ms": 0,
            "le_0_5ms": 0,
            "le_1ms": 0,
            "le_2_5ms": 0,
            "le_5ms": 0,
            "le_10ms": 0,
            "le_25ms": 0,
            "le_50ms": 0,
            "le_100ms": 0,
            "gt_100ms": 0,
        },
        description="Histogram bucket counts for latency distribution analysis.",
    )

    # ---- Per-Step Breakdowns ----
    step_totals_ms: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Cumulative latency per named validation step in milliseconds. "
            "Keys are step names (e.g., 'envelope_structure', 'correlation_id')."
        ),
    )
    step_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Number of observations per named validation step.",
    )

    # ---- Metadata ----
    last_recorded_at: datetime | None = Field(
        default=None,
        description="Timestamp of the most recent validation observation.",
    )

    # ---- Computed Properties ----

    @property
    def avg_duration_ms(self) -> float:
        """Average validation latency in milliseconds.

        Returns:
            Average duration in milliseconds, or ``0.0`` if no validations.
        """
        if self.total_validations == 0:
            return 0.0
        return self.total_duration_ms / self.total_validations

    @property
    def pass_rate(self) -> float:
        """Fraction of validations that passed (0.0-1.0).

        Returns:
            Pass rate as a decimal, or ``1.0`` if no validations recorded.
        """
        if self.total_validations == 0:
            return 1.0
        return self.passed_validations / self.total_validations

    @property
    def failure_rate(self) -> float:
        """Fraction of validations that failed (0.0-1.0).

        Returns:
            Failure rate as a decimal, or ``0.0`` if no validations recorded.
        """
        if self.total_validations == 0:
            return 0.0
        return self.failed_validations / self.total_validations

    @property
    def p50_duration_ms(self) -> float | None:
        """Estimated p50 (median) latency from histogram buckets.

        Returns the upper bound of the bucket containing the 50th percentile
        observation, or ``None`` if no validations have been recorded.

        Returns:
            Estimated p50 latency in milliseconds, or ``None``.
        """
        return self._percentile_estimate(0.50)

    @property
    def p95_duration_ms(self) -> float | None:
        """Estimated p95 latency from histogram buckets.

        Returns:
            Estimated p95 latency in milliseconds, or ``None``.
        """
        return self._percentile_estimate(0.95)

    @property
    def p99_duration_ms(self) -> float | None:
        """Estimated p99 latency from histogram buckets.

        Returns:
            Estimated p99 latency in milliseconds, or ``None``.
        """
        return self._percentile_estimate(0.99)

    # ---- Public Methods ----

    def record_validation(
        self,
        total_duration_ms: float,
        passed: bool,
        step_durations_ms: dict[str, float] | None = None,
    ) -> ModelEnvelopeValidationTimingMetrics:
        """Record a single validation operation and return updated metrics.

        Creates a new immutable instance with updated statistics. The original
        instance is never mutated.

        Args:
            total_duration_ms: Total duration of the validation operation.
            passed: Whether the validation passed.
            step_durations_ms: Optional per-step duration breakdown. Keys are
                step names (e.g., ``"envelope_structure"``, ``"correlation_id"``).

        Returns:
            New ``ModelEnvelopeValidationTimingMetrics`` with updated statistics.

        Example:
            >>> metrics = ModelEnvelopeValidationTimingMetrics()
            >>> metrics = metrics.record_validation(
            ...     total_duration_ms=1.2,
            ...     passed=True,
            ...     step_durations_ms={"correlation_id": 0.4},
            ... )
            >>> metrics.total_validations
            1
        """
        new_min = (
            total_duration_ms
            if self.min_duration_ms is None
            else min(self.min_duration_ms, total_duration_ms)
        )
        new_max = (
            total_duration_ms
            if self.max_duration_ms is None
            else max(self.max_duration_ms, total_duration_ms)
        )

        bucket_key = self._histogram_bucket(total_duration_ms)
        new_histogram = dict(self.latency_histogram)
        new_histogram[bucket_key] = new_histogram.get(bucket_key, 0) + 1

        new_step_totals = dict(self.step_totals_ms)
        new_step_counts = dict(self.step_counts)
        if step_durations_ms:
            for step, duration in step_durations_ms.items():
                new_step_totals[step] = new_step_totals.get(step, 0.0) + duration
                new_step_counts[step] = new_step_counts.get(step, 0) + 1

        return ModelEnvelopeValidationTimingMetrics(
            total_validations=self.total_validations + 1,
            passed_validations=self.passed_validations + (1 if passed else 0),
            failed_validations=self.failed_validations + (0 if passed else 1),
            total_duration_ms=self.total_duration_ms + total_duration_ms,
            min_duration_ms=new_min,
            max_duration_ms=new_max,
            latency_histogram=new_histogram,
            step_totals_ms=new_step_totals,
            step_counts=new_step_counts,
            last_recorded_at=datetime.now(UTC),
        )

    def get_step_avg_ms(self, step_name: str) -> float | None:
        """Average latency for a specific validation step.

        Args:
            step_name: The validation step name (e.g., ``"correlation_id"``).

        Returns:
            Average step latency in milliseconds, or ``None`` if the step has
            not been observed.
        """
        count = self.step_counts.get(step_name, 0)
        if count == 0:
            return None
        return self.step_totals_ms.get(step_name, 0.0) / count

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary including computed properties.

        Returns:
            Dictionary with all fields and computed percentile estimates.
        """
        return {
            "total_validations": self.total_validations,
            "passed_validations": self.passed_validations,
            "failed_validations": self.failed_validations,
            "avg_duration_ms": self.avg_duration_ms,
            "min_duration_ms": self.min_duration_ms,
            "max_duration_ms": self.max_duration_ms,
            "p50_duration_ms": self.p50_duration_ms,
            "p95_duration_ms": self.p95_duration_ms,
            "p99_duration_ms": self.p99_duration_ms,
            "pass_rate": self.pass_rate,
            "failure_rate": self.failure_rate,
            "total_duration_ms": self.total_duration_ms,
            "latency_histogram": self.latency_histogram,
            "step_totals_ms": self.step_totals_ms,
            "step_counts": self.step_counts,
            "last_recorded_at": (
                self.last_recorded_at.isoformat() if self.last_recorded_at else None
            ),
        }

    @classmethod
    def create_empty(cls) -> ModelEnvelopeValidationTimingMetrics:
        """Create a new empty metrics instance.

        Returns:
            New ``ModelEnvelopeValidationTimingMetrics`` with zero counters.
        """
        return cls()

    # ---- Private Helpers ----

    @staticmethod
    def _histogram_bucket(duration_ms: float) -> str:
        """Map a latency value to its histogram bucket key."""
        _bucket_map: list[tuple[float, str]] = [
            (0.1, "le_0_1ms"),
            (0.25, "le_0_25ms"),
            (0.5, "le_0_5ms"),
            (1.0, "le_1ms"),
            (2.5, "le_2_5ms"),
            (5.0, "le_5ms"),
            (10.0, "le_10ms"),
            (25.0, "le_25ms"),
            (50.0, "le_50ms"),
            (100.0, "le_100ms"),
        ]
        for threshold, key in _bucket_map:
            if duration_ms <= threshold:
                return key
        return "gt_100ms"

    def _percentile_estimate(self, percentile: float) -> float | None:
        """Estimate a percentile latency from histogram buckets.

        Uses the upper bucket boundary as the estimate — consistent with how
        Prometheus exposes histogram_quantile.

        Args:
            percentile: Target percentile fraction (e.g., ``0.95`` for p95).

        Returns:
            Upper bound of the bucket containing the target percentile,
            or ``None`` if no observations recorded.
        """
        if self.total_validations == 0:
            return None

        target_count = self.total_validations * percentile
        cumulative = 0

        _ordered_buckets: list[tuple[str, float]] = [
            ("le_0_1ms", 0.1),
            ("le_0_25ms", 0.25),
            ("le_0_5ms", 0.5),
            ("le_1ms", 1.0),
            ("le_2_5ms", 2.5),
            ("le_5ms", 5.0),
            ("le_10ms", 10.0),
            ("le_25ms", 25.0),
            ("le_50ms", 50.0),
            ("le_100ms", 100.0),
            ("gt_100ms", float("inf")),
        ]

        for bucket_key, upper_bound in _ordered_buckets:
            cumulative += self.latency_histogram.get(bucket_key, 0)
            if cumulative >= target_count:
                return upper_bound

        return None


__all__ = [
    "ModelEnvelopeValidationTimingMetrics",
    "VALIDATION_LATENCY_HISTOGRAM_BUCKETS",
]
