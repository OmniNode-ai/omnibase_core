# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelEnvelopeValidationFailureMetrics."""

import pytest

from omnibase_core.enums.enum_envelope_validation_failure_type import (
    EnumEnvelopeValidationFailureType,
)
from omnibase_core.models.observability.model_envelope_validation_failure_metrics import (
    DEFAULT_CORRELATION_ID_GENERATION_ALERT_THRESHOLD,
    DEFAULT_FAILURE_RATE_ALERT_THRESHOLD,
    ModelEnvelopeValidationFailureMetrics,
)


class TestModelEnvelopeValidationFailureMetricsDefaults:
    """Tests for ModelEnvelopeValidationFailureMetrics default values."""

    def test_default_zero_counters(self) -> None:
        """Default instance has all counters at zero."""
        m = ModelEnvelopeValidationFailureMetrics()
        assert m.total_validations == 0
        assert m.total_failures == 0

    def test_default_failure_rate(self) -> None:
        """Default failure_rate is 0.0 with no observations."""
        m = ModelEnvelopeValidationFailureMetrics()
        assert m.failure_rate == 0.0

    def test_default_pass_rate(self) -> None:
        """Default pass_rate is 1.0 with no observations."""
        m = ModelEnvelopeValidationFailureMetrics()
        assert m.pass_rate == 1.0

    def test_default_thresholds(self) -> None:
        """Default alerting thresholds match module-level constants."""
        m = ModelEnvelopeValidationFailureMetrics()
        assert m.failure_rate_alert_threshold == DEFAULT_FAILURE_RATE_ALERT_THRESHOLD
        assert (
            m.correlation_generation_alert_threshold
            == DEFAULT_CORRELATION_ID_GENERATION_ALERT_THRESHOLD
        )

    def test_default_failures_by_type_all_zero(self) -> None:
        """Default failures_by_type has all failure types at zero."""
        m = ModelEnvelopeValidationFailureMetrics()
        for ft in EnumEnvelopeValidationFailureType:
            assert m.failures_by_type[ft.value] == 0

    def test_create_empty_factory(self) -> None:
        """create_empty() returns an empty instance."""
        m = ModelEnvelopeValidationFailureMetrics.create_empty()
        assert m.total_validations == 0
        assert m.total_failures == 0


class TestModelEnvelopeValidationFailureMetricsRecordFailure:
    """Tests for record_failure() accumulation."""

    def test_record_single_failure_increments_counts(self) -> None:
        """Recording a failure increments total_validations and total_failures."""
        m = ModelEnvelopeValidationFailureMetrics()
        updated = m.record_failure(EnumEnvelopeValidationFailureType.MISSING_CORRELATION_ID)

        assert updated.total_validations == 1
        assert updated.total_failures == 1
        assert updated.failures_by_type["missing_correlation_id"] == 1

    def test_record_failure_immutability(self) -> None:
        """record_failure does not mutate the original instance."""
        original = ModelEnvelopeValidationFailureMetrics()
        _ = original.record_failure(EnumEnvelopeValidationFailureType.EMPTY_PAYLOAD)
        assert original.total_validations == 0

    def test_record_multiple_failure_types(self) -> None:
        """Multiple different failure types are tracked independently."""
        m = ModelEnvelopeValidationFailureMetrics()
        m = m.record_failure(EnumEnvelopeValidationFailureType.MISSING_CORRELATION_ID)
        m = m.record_failure(EnumEnvelopeValidationFailureType.EMPTY_PAYLOAD)
        m = m.record_failure(EnumEnvelopeValidationFailureType.MISSING_CORRELATION_ID)

        assert m.failures_by_type["missing_correlation_id"] == 2
        assert m.failures_by_type["empty_payload"] == 1
        assert m.total_failures == 3

    def test_failure_rate_computed_correctly(self) -> None:
        """Failure rate is total_failures / total_validations."""
        m = ModelEnvelopeValidationFailureMetrics()
        for _ in range(3):
            m = m.record_pass()
        m = m.record_failure(EnumEnvelopeValidationFailureType.TYPE_MISMATCH)

        assert m.failure_rate == pytest.approx(0.25)
        assert m.pass_rate == pytest.approx(0.75)

    def test_get_failure_count(self) -> None:
        """get_failure_count returns correct count for a specific type."""
        m = ModelEnvelopeValidationFailureMetrics()
        m = m.record_failure(EnumEnvelopeValidationFailureType.INVALID_ENVELOPE_STRUCTURE)
        m = m.record_failure(EnumEnvelopeValidationFailureType.INVALID_ENVELOPE_STRUCTURE)

        assert m.get_failure_count(EnumEnvelopeValidationFailureType.INVALID_ENVELOPE_STRUCTURE) == 2
        assert m.get_failure_count(EnumEnvelopeValidationFailureType.EMPTY_PAYLOAD) == 0

    def test_get_failure_rate_for_type(self) -> None:
        """get_failure_rate_for_type returns correct fraction."""
        m = ModelEnvelopeValidationFailureMetrics()
        for _ in range(8):
            m = m.record_pass()
        m = m.record_failure(EnumEnvelopeValidationFailureType.MISSING_MESSAGE_ID)
        m = m.record_failure(EnumEnvelopeValidationFailureType.MISSING_MESSAGE_ID)

        rate = m.get_failure_rate_for_type(EnumEnvelopeValidationFailureType.MISSING_MESSAGE_ID)
        assert rate == pytest.approx(0.2)


class TestModelEnvelopeValidationFailureMetricsRecordPass:
    """Tests for record_pass() accumulation."""

    def test_record_pass_does_not_increment_failures(self) -> None:
        """Passing validation increments total_validations but not total_failures."""
        m = ModelEnvelopeValidationFailureMetrics()
        updated = m.record_pass()

        assert updated.total_validations == 1
        assert updated.total_failures == 0

    def test_record_pass_with_generated_correlation_id(self) -> None:
        """Passing with generated correlation ID increments generation counter."""
        m = ModelEnvelopeValidationFailureMetrics()
        m = m.record_pass(correlation_id_was_generated=True)

        assert m.correlation_ids_generated == 1
        assert m.correlation_ids_propagated == 0

    def test_record_pass_with_propagated_correlation_id(self) -> None:
        """Passing with propagated correlation ID increments propagation counter."""
        m = ModelEnvelopeValidationFailureMetrics()
        m = m.record_pass(correlation_id_was_generated=False)

        assert m.correlation_ids_generated == 0
        assert m.correlation_ids_propagated == 1

    def test_correlation_id_generation_ratio(self) -> None:
        """Generation ratio is computed correctly from generated/propagated counts."""
        m = ModelEnvelopeValidationFailureMetrics()
        for _ in range(3):
            m = m.record_pass(correlation_id_was_generated=True)
        for _ in range(7):
            m = m.record_pass(correlation_id_was_generated=False)

        assert m.correlation_id_generation_ratio == pytest.approx(0.3)

    def test_correlation_id_generation_ratio_zero_total(self) -> None:
        """Generation ratio is 0.0 when no correlation IDs observed."""
        m = ModelEnvelopeValidationFailureMetrics()
        assert m.correlation_id_generation_ratio == 0.0


class TestModelEnvelopeValidationFailureMetricsAlerting:
    """Tests for alerting threshold evaluation."""

    def test_failure_rate_not_elevated_below_threshold(self) -> None:
        """Failure rate below threshold does not trigger alert."""
        m = ModelEnvelopeValidationFailureMetrics()
        for _ in range(100):
            m = m.record_pass()
        # 2% failure rate — below 5% default threshold
        m = m.record_failure(EnumEnvelopeValidationFailureType.UNKNOWN)
        m = m.record_failure(EnumEnvelopeValidationFailureType.UNKNOWN)

        assert not m.is_failure_rate_elevated()

    def test_failure_rate_elevated_above_threshold(self) -> None:
        """Failure rate above threshold triggers alert."""
        m = ModelEnvelopeValidationFailureMetrics()
        for _ in range(4):
            m = m.record_pass()
        m = m.record_failure(EnumEnvelopeValidationFailureType.UNKNOWN)
        # 20% failure rate — above 5% default threshold
        assert m.is_failure_rate_elevated()

    def test_custom_failure_rate_threshold(self) -> None:
        """Custom failure rate threshold is respected."""
        m = ModelEnvelopeValidationFailureMetrics(failure_rate_alert_threshold=0.5)
        for _ in range(3):
            m = m.record_pass()
        m = m.record_failure(EnumEnvelopeValidationFailureType.UNKNOWN)
        # 25% failure rate — below custom 50% threshold
        assert not m.is_failure_rate_elevated()

    def test_correlation_id_generation_elevated(self) -> None:
        """High generation ratio triggers correlation ID alert."""
        m = ModelEnvelopeValidationFailureMetrics()
        # 50% generation ratio — above 20% default threshold
        for _ in range(5):
            m = m.record_pass(correlation_id_was_generated=True)
        for _ in range(5):
            m = m.record_pass(correlation_id_was_generated=False)

        assert m.is_correlation_id_generation_elevated()

    def test_correlation_id_generation_not_elevated(self) -> None:
        """Low generation ratio does not trigger correlation ID alert."""
        m = ModelEnvelopeValidationFailureMetrics()
        # 10% generation ratio — below 20% default threshold
        m = m.record_pass(correlation_id_was_generated=True)
        for _ in range(9):
            m = m.record_pass(correlation_id_was_generated=False)

        assert not m.is_correlation_id_generation_elevated()

    def test_last_recorded_at_updated(self) -> None:
        """last_recorded_at is set after recording a failure."""
        m = ModelEnvelopeValidationFailureMetrics()
        assert m.last_recorded_at is None
        updated = m.record_failure(EnumEnvelopeValidationFailureType.UNKNOWN)
        assert updated.last_recorded_at is not None


class TestModelEnvelopeValidationFailureMetricsToDict:
    """Tests for to_dict() serialization."""

    def test_to_dict_keys(self) -> None:
        """to_dict() returns all expected top-level keys."""
        m = ModelEnvelopeValidationFailureMetrics()
        result = m.to_dict()
        expected_keys = {
            "total_validations",
            "total_failures",
            "failure_rate",
            "pass_rate",
            "failures_by_type",
            "correlation_ids_generated",
            "correlation_ids_propagated",
            "correlation_id_generation_ratio",
            "is_failure_rate_elevated",
            "is_correlation_id_generation_elevated",
            "failure_rate_alert_threshold",
            "correlation_generation_alert_threshold",
            "last_recorded_at",
        }
        assert set(result.keys()) == expected_keys
