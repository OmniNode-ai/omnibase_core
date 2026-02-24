# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Envelope Validation Summary Model.

Combines timing metrics and failure metrics into a unified observability
snapshot for the envelope validation subsystem. Suitable for Prometheus
metric exposition and Grafana dashboard queries.

Design Pattern:
    Composite model that aggregates ``ModelEnvelopeValidationTimingMetrics``
    and ``ModelEnvelopeValidationFailureMetrics``. Provides convenience factory
    methods and a ``record_validation()`` method that updates both sub-models
    atomically.

Thread Safety:
    All instances are frozen (immutable). Callers must synchronise externally.

Example:
    >>> from omnibase_core.models.observability import ModelEnvelopeValidationSummary
    >>> from omnibase_core.enums import EnumEnvelopeValidationFailureType
    >>>
    >>> summary = ModelEnvelopeValidationSummary.create_empty()
    >>> summary = summary.record_validation(
    ...     total_duration_ms=1.5,
    ...     passed=True,
    ...     step_durations_ms={"correlation_id": 0.4, "envelope_structure": 0.8},
    ...     correlation_id_was_generated=False,
    ... )
    >>> summary = summary.record_validation(
    ...     total_duration_ms=0.3,
    ...     passed=False,
    ...     failure_type=EnumEnvelopeValidationFailureType.MISSING_CORRELATION_ID,
    ... )
    >>> print(f"p95: {summary.timing.p95_duration_ms}")
    >>> print(f"failure rate: {summary.failures.failure_rate:.0%}")

See Also:
    - ``ModelEnvelopeValidationTimingMetrics``: Timing sub-model
    - ``ModelEnvelopeValidationFailureMetrics``: Failure sub-model
    - ``EnumEnvelopeValidationFailureType``: Failure type taxonomy

.. versionadded:: 0.6.0
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_envelope_validation_failure_type import (
    EnumEnvelopeValidationFailureType,
)
from omnibase_core.models.observability.model_envelope_validation_failure_metrics import (
    ModelEnvelopeValidationFailureMetrics,
)
from omnibase_core.models.observability.model_envelope_validation_timing_metrics import (
    ModelEnvelopeValidationTimingMetrics,
)


class ModelEnvelopeValidationSummary(BaseModel):
    """Combined timing and failure metrics snapshot for envelope validation.

    Aggregates both the timing sub-model and failure sub-model into a single
    immutable snapshot. Use ``record_validation()`` to atomically update both
    sub-models.

    Attributes:
        timing: Per-operation latency statistics with p50/p95/p99 estimates.
        failures: Per-type failure counts, rates, and alerting state.
        created_at: Timestamp when this summary instance was created.

    Example:
        >>> summary = ModelEnvelopeValidationSummary.create_empty()
        >>> summary = summary.record_validation(
        ...     total_duration_ms=0.8,
        ...     passed=True,
        ... )
        >>> summary.timing.total_validations
        1
        >>> summary.failures.total_validations
        1
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    timing: ModelEnvelopeValidationTimingMetrics = Field(
        default_factory=ModelEnvelopeValidationTimingMetrics,
        description="Latency statistics for envelope validation operations.",
    )
    failures: ModelEnvelopeValidationFailureMetrics = Field(
        default_factory=ModelEnvelopeValidationFailureMetrics,
        description="Failure rate and per-type breakdown for envelope validation.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when this summary instance was first created.",
    )

    # ---- Alerting ----

    @property
    def has_elevated_failure_rate(self) -> bool:
        """Whether the failure rate exceeds the configured alert threshold.

        Returns:
            ``True`` if ``failures.is_failure_rate_elevated()`` is ``True``.
        """
        return self.failures.is_failure_rate_elevated()

    @property
    def has_elevated_correlation_id_generation(self) -> bool:
        """Whether correlation ID generation ratio is unexpectedly high.

        Returns:
            ``True`` if ``failures.is_correlation_id_generation_elevated()`` is ``True``.
        """
        return self.failures.is_correlation_id_generation_elevated()

    # ---- Accumulation ----

    def record_validation(
        self,
        total_duration_ms: float,
        passed: bool,
        step_durations_ms: dict[str, float] | None = None,
        failure_type: EnumEnvelopeValidationFailureType | None = None,
        correlation_id_was_generated: bool = False,
    ) -> ModelEnvelopeValidationSummary:
        """Record a single validation operation and return updated summary.

        Atomically updates both the timing and failure sub-models. When
        ``passed=False``, provide ``failure_type`` to record the failure
        category. When ``passed=True``, provide ``correlation_id_was_generated``
        to track the generation vs propagation ratio.

        Args:
            total_duration_ms: Total duration of the validation operation.
            passed: Whether the validation passed.
            step_durations_ms: Optional per-step duration breakdown. Keys should
                be step names (e.g., ``"envelope_structure"``, ``"correlation_id"``,
                ``"payload_presence"``).
            failure_type: Required when ``passed=False``. Ignored when ``passed=True``.
                Defaults to ``UNKNOWN`` if ``passed=False`` and not provided.
            correlation_id_was_generated: When ``passed=True``, indicates whether
                the correlation ID was auto-generated rather than propagated.

        Returns:
            New ``ModelEnvelopeValidationSummary`` with updated sub-models.

        Example:
            >>> summary = ModelEnvelopeValidationSummary.create_empty()
            >>> summary = summary.record_validation(
            ...     total_duration_ms=1.2,
            ...     passed=True,
            ...     step_durations_ms={"correlation_id": 0.5},
            ...     correlation_id_was_generated=True,
            ... )
        """
        new_timing = self.timing.record_validation(
            total_duration_ms=total_duration_ms,
            passed=passed,
            step_durations_ms=step_durations_ms,
        )

        if passed:
            new_failures = self.failures.record_pass(
                correlation_id_was_generated=correlation_id_was_generated,
            )
        else:
            resolved_failure_type = (
                failure_type
                if failure_type is not None
                else EnumEnvelopeValidationFailureType.UNKNOWN
            )
            new_failures = self.failures.record_failure(resolved_failure_type)

        return ModelEnvelopeValidationSummary(
            timing=new_timing,
            failures=new_failures,
            created_at=self.created_at,
        )

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary including all sub-model data.

        Returns:
            Dictionary with ``timing``, ``failures``, and ``alerts`` sections.
        """
        return {
            "timing": self.timing.to_dict(),
            "failures": self.failures.to_dict(),
            "alerts": {
                "elevated_failure_rate": self.has_elevated_failure_rate,
                "elevated_correlation_id_generation": (
                    self.has_elevated_correlation_id_generation
                ),
            },
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def create_empty(cls) -> ModelEnvelopeValidationSummary:
        """Create a new empty summary instance.

        Returns:
            New ``ModelEnvelopeValidationSummary`` with zeroed sub-models.
        """
        return cls(
            timing=ModelEnvelopeValidationTimingMetrics.create_empty(),
            failures=ModelEnvelopeValidationFailureMetrics.create_empty(),
        )


__all__ = ["ModelEnvelopeValidationSummary"]
