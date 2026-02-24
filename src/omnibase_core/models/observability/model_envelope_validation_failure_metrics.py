# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Envelope Validation Failure Rate Metrics Model.

Immutable model tracking validation failure counts and rates broken down by
``EnumEnvelopeValidationFailureType``. Provides alerting threshold evaluation
for elevated failure rates and correlation ID monitoring (generated vs propagated).

Design Pattern:
    Follows the same immutable accumulator pattern as ``ModelDispatchMetrics``.
    Call ``record_failure()`` or ``record_pass()`` to produce updated instances.

Thread Safety:
    All instances are frozen (immutable). Callers must synchronise externally.

Example:
    >>> from omnibase_core.models.observability import ModelEnvelopeValidationFailureMetrics
    >>> from omnibase_core.enums import EnumEnvelopeValidationFailureType
    >>>
    >>> metrics = ModelEnvelopeValidationFailureMetrics()
    >>> metrics = metrics.record_failure(
    ...     EnumEnvelopeValidationFailureType.MISSING_CORRELATION_ID
    ... )
    >>> metrics.failure_rate
    1.0
    >>> metrics = metrics.record_pass()
    >>> metrics.failure_rate
    0.5

See Also:
    - ``ModelEnvelopeValidationTimingMetrics``: Companion timing model
    - ``ModelEnvelopeValidationSummary``: Combined summary model
    - ``EnumEnvelopeValidationFailureType``: Failure type taxonomy

.. versionadded:: 0.6.0
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_envelope_validation_failure_type import (
    EnumEnvelopeValidationFailureType,
)

# Default alerting threshold: alert when failure rate exceeds 5%
DEFAULT_FAILURE_RATE_ALERT_THRESHOLD: float = 0.05

# Default alerting threshold: alert when correlation ID generation ratio exceeds 20%
DEFAULT_CORRELATION_ID_GENERATION_ALERT_THRESHOLD: float = 0.20


class ModelEnvelopeValidationFailureMetrics(BaseModel):
    """Immutable failure rate metrics for envelope validation.

    Tracks validation outcomes broken down by failure type and provides
    alerting threshold evaluation for anomaly detection.

    Attributes:
        total_validations: Total validation observations recorded.
        total_failures: Total failed validation observations.
        failures_by_type: Failure counts keyed by ``EnumEnvelopeValidationFailureType``.
        correlation_ids_generated: Count of correlation IDs auto-generated.
        correlation_ids_propagated: Count of correlation IDs propagated from upstream.
        failure_rate_alert_threshold: Alert when failure rate exceeds this fraction.
        correlation_generation_alert_threshold: Alert when generation ratio exceeds
            this fraction.
        last_recorded_at: Timestamp of the most recent observation.

    Example:
        >>> m = ModelEnvelopeValidationFailureMetrics()
        >>> m = m.record_failure(EnumEnvelopeValidationFailureType.EMPTY_PAYLOAD)
        >>> m.is_failure_rate_elevated()
        False  # only 1 data point, depends on threshold
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
        description="Total number of validation observations recorded.",
    )
    total_failures: int = Field(
        default=0,
        ge=0,
        description="Total number of failed validation observations.",
    )

    # ---- Failures by Type ----
    failures_by_type: dict[str, int] = Field(
        default_factory=lambda: {
            EnumEnvelopeValidationFailureType.MISSING_CORRELATION_ID.value: 0,
            EnumEnvelopeValidationFailureType.INVALID_ENVELOPE_STRUCTURE.value: 0,
            EnumEnvelopeValidationFailureType.EMPTY_PAYLOAD.value: 0,
            EnumEnvelopeValidationFailureType.TYPE_MISMATCH.value: 0,
            EnumEnvelopeValidationFailureType.MISSING_MESSAGE_ID.value: 0,
            EnumEnvelopeValidationFailureType.MISSING_ENTITY_ID.value: 0,
            EnumEnvelopeValidationFailureType.UNKNOWN.value: 0,
        },
        description=(
            "Failure counts keyed by EnumEnvelopeValidationFailureType string value."
        ),
    )

    # ---- Correlation ID Monitoring ----
    correlation_ids_generated: int = Field(
        default=0,
        ge=0,
        description="Count of correlation IDs auto-generated (UUID created by receiver).",
    )
    correlation_ids_propagated: int = Field(
        default=0,
        ge=0,
        description="Count of correlation IDs propagated from upstream callers.",
    )

    # ---- Alerting Thresholds ----
    failure_rate_alert_threshold: float = Field(
        default=DEFAULT_FAILURE_RATE_ALERT_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Alert when failure rate exceeds this fraction (default 0.05 = 5%).",
    )
    correlation_generation_alert_threshold: float = Field(
        default=DEFAULT_CORRELATION_ID_GENERATION_ALERT_THRESHOLD,
        ge=0.0,
        le=1.0,
        description=(
            "Alert when correlation ID generation ratio exceeds this fraction "
            "(default 0.20 = 20%)."
        ),
    )

    # ---- Metadata ----
    last_recorded_at: datetime | None = Field(
        default=None,
        description="Timestamp of the most recent observation.",
    )

    # ---- Computed Properties ----

    @property
    def failure_rate(self) -> float:
        """Overall validation failure rate (0.0–1.0).

        Returns:
            Failure rate as a decimal, or ``0.0`` if no validations recorded.
        """
        if self.total_validations == 0:
            return 0.0
        return self.total_failures / self.total_validations

    @property
    def pass_rate(self) -> float:
        """Overall validation pass rate (0.0–1.0).

        Returns:
            Pass rate as a decimal, or ``1.0`` if no validations recorded.
        """
        return 1.0 - self.failure_rate

    @property
    def correlation_id_generation_ratio(self) -> float:
        """Fraction of validations where a correlation ID was auto-generated.

        Returns:
            Generation ratio as a decimal, or ``0.0`` if no validations.
        """
        total_correlation = (
            self.correlation_ids_generated + self.correlation_ids_propagated
        )
        if total_correlation == 0:
            return 0.0
        return self.correlation_ids_generated / total_correlation

    # ---- Alerting Methods ----

    def is_failure_rate_elevated(self) -> bool:
        """Check whether the failure rate exceeds the configured alert threshold.

        Returns:
            ``True`` if failure rate exceeds ``failure_rate_alert_threshold``.
        """
        return self.failure_rate > self.failure_rate_alert_threshold

    def is_correlation_id_generation_elevated(self) -> bool:
        """Check whether correlation ID generation ratio is unexpectedly high.

        A high generation ratio may indicate that upstream callers are not
        propagating correlation IDs correctly.

        Returns:
            ``True`` if generation ratio exceeds ``correlation_generation_alert_threshold``.
        """
        return (
            self.correlation_id_generation_ratio
            > self.correlation_generation_alert_threshold
        )

    # ---- Accumulation Methods ----

    def record_failure(
        self,
        failure_type: EnumEnvelopeValidationFailureType,
    ) -> "ModelEnvelopeValidationFailureMetrics":
        """Record a validation failure and return updated metrics.

        Args:
            failure_type: The ``EnumEnvelopeValidationFailureType`` classification
                of the failure.

        Returns:
            New ``ModelEnvelopeValidationFailureMetrics`` with updated counts.

        Example:
            >>> m = ModelEnvelopeValidationFailureMetrics()
            >>> m = m.record_failure(EnumEnvelopeValidationFailureType.MISSING_CORRELATION_ID)
            >>> m.failures_by_type["missing_correlation_id"]
            1
        """
        new_failures_by_type = dict(self.failures_by_type)
        key = failure_type.value
        new_failures_by_type[key] = new_failures_by_type.get(key, 0) + 1

        return ModelEnvelopeValidationFailureMetrics(
            total_validations=self.total_validations + 1,
            total_failures=self.total_failures + 1,
            failures_by_type=new_failures_by_type,
            correlation_ids_generated=self.correlation_ids_generated,
            correlation_ids_propagated=self.correlation_ids_propagated,
            failure_rate_alert_threshold=self.failure_rate_alert_threshold,
            correlation_generation_alert_threshold=self.correlation_generation_alert_threshold,
            last_recorded_at=datetime.now(UTC),
        )

    def record_pass(
        self,
        correlation_id_was_generated: bool = False,
    ) -> "ModelEnvelopeValidationFailureMetrics":
        """Record a successful validation and return updated metrics.

        Args:
            correlation_id_was_generated: If ``True``, the correlation ID was
                auto-generated by the receiver rather than propagated from upstream.
                Used to track the generation vs propagation ratio.

        Returns:
            New ``ModelEnvelopeValidationFailureMetrics`` with updated counts.

        Example:
            >>> m = ModelEnvelopeValidationFailureMetrics()
            >>> m = m.record_pass(correlation_id_was_generated=True)
            >>> m.correlation_id_generation_ratio
            1.0
        """
        return ModelEnvelopeValidationFailureMetrics(
            total_validations=self.total_validations + 1,
            total_failures=self.total_failures,
            failures_by_type=dict(self.failures_by_type),
            correlation_ids_generated=(
                self.correlation_ids_generated + (1 if correlation_id_was_generated else 0)
            ),
            correlation_ids_propagated=(
                self.correlation_ids_propagated
                + (0 if correlation_id_was_generated else 1)
            ),
            failure_rate_alert_threshold=self.failure_rate_alert_threshold,
            correlation_generation_alert_threshold=self.correlation_generation_alert_threshold,
            last_recorded_at=datetime.now(UTC),
        )

    def get_failure_count(
        self,
        failure_type: EnumEnvelopeValidationFailureType,
    ) -> int:
        """Get the failure count for a specific failure type.

        Args:
            failure_type: The failure type to query.

        Returns:
            Number of failures of this type recorded.
        """
        return self.failures_by_type.get(failure_type.value, 0)

    def get_failure_rate_for_type(
        self,
        failure_type: EnumEnvelopeValidationFailureType,
    ) -> float:
        """Failure rate for a specific failure type relative to total validations.

        Args:
            failure_type: The failure type to query.

        Returns:
            Fraction of total validations that failed with this type, or ``0.0``.
        """
        if self.total_validations == 0:
            return 0.0
        count = self.get_failure_count(failure_type)
        return count / self.total_validations

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary including computed properties.

        Returns:
            Dictionary with all fields and computed rates.
        """
        return {
            "total_validations": self.total_validations,
            "total_failures": self.total_failures,
            "failure_rate": self.failure_rate,
            "pass_rate": self.pass_rate,
            "failures_by_type": self.failures_by_type,
            "correlation_ids_generated": self.correlation_ids_generated,
            "correlation_ids_propagated": self.correlation_ids_propagated,
            "correlation_id_generation_ratio": self.correlation_id_generation_ratio,
            "is_failure_rate_elevated": self.is_failure_rate_elevated(),
            "is_correlation_id_generation_elevated": (
                self.is_correlation_id_generation_elevated()
            ),
            "failure_rate_alert_threshold": self.failure_rate_alert_threshold,
            "correlation_generation_alert_threshold": (
                self.correlation_generation_alert_threshold
            ),
            "last_recorded_at": (
                self.last_recorded_at.isoformat() if self.last_recorded_at else None
            ),
        }

    @classmethod
    def create_empty(cls) -> "ModelEnvelopeValidationFailureMetrics":
        """Create a new empty metrics instance.

        Returns:
            New ``ModelEnvelopeValidationFailureMetrics`` with zero counters.
        """
        return cls()


__all__ = [
    "ModelEnvelopeValidationFailureMetrics",
    "DEFAULT_FAILURE_RATE_ALERT_THRESHOLD",
    "DEFAULT_CORRELATION_ID_GENERATION_ALERT_THRESHOLD",
]
