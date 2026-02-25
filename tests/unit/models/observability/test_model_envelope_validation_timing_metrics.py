# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelEnvelopeValidationTimingMetrics."""

import pytest

from omnibase_core.models.observability.model_envelope_validation_timing_metrics import (
    VALIDATION_LATENCY_HISTOGRAM_BUCKETS,
    ModelEnvelopeValidationTimingMetrics,
)


class TestModelEnvelopeValidationTimingMetricsDefaults:
    """Tests for ModelEnvelopeValidationTimingMetrics default values."""

    def test_default_zero_counters(self) -> None:
        """Default instance has all counters at zero."""
        m = ModelEnvelopeValidationTimingMetrics()
        assert m.total_validations == 0
        assert m.passed_validations == 0
        assert m.failed_validations == 0

    def test_default_latency_fields(self) -> None:
        """Default instance has zero latency totals and None min/max."""
        m = ModelEnvelopeValidationTimingMetrics()
        assert m.total_duration_ms == 0.0
        assert m.min_duration_ms is None
        assert m.max_duration_ms is None

    def test_default_computed_properties(self) -> None:
        """Default instance computed properties return neutral values."""
        m = ModelEnvelopeValidationTimingMetrics()
        assert m.avg_duration_ms == 0.0
        assert m.pass_rate == 1.0
        assert m.failure_rate == 0.0

    def test_default_percentiles_are_none(self) -> None:
        """Percentile estimates are None when no validations recorded."""
        m = ModelEnvelopeValidationTimingMetrics()
        assert m.p50_duration_ms is None
        assert m.p95_duration_ms is None
        assert m.p99_duration_ms is None

    def test_default_histogram_keys(self) -> None:
        """Histogram has the expected bucket keys."""
        m = ModelEnvelopeValidationTimingMetrics()
        expected_keys = {
            "le_0_1ms",
            "le_0_25ms",
            "le_0_5ms",
            "le_1ms",
            "le_2_5ms",
            "le_5ms",
            "le_10ms",
            "le_25ms",
            "le_50ms",
            "le_100ms",
            "gt_100ms",
        }
        assert set(m.latency_histogram.keys()) == expected_keys

    def test_create_empty_factory(self) -> None:
        """create_empty() returns equivalent to default constructor."""
        m = ModelEnvelopeValidationTimingMetrics.create_empty()
        assert m.total_validations == 0
        assert m.passed_validations == 0


class TestModelEnvelopeValidationTimingMetricsRecordValidation:
    """Tests for record_validation() accumulation."""

    def test_record_single_pass(self) -> None:
        """Recording one passing validation increments all counts correctly."""
        m = ModelEnvelopeValidationTimingMetrics()
        updated = m.record_validation(total_duration_ms=2.0, passed=True)

        assert updated.total_validations == 1
        assert updated.passed_validations == 1
        assert updated.failed_validations == 0
        assert updated.total_duration_ms == 2.0
        assert updated.min_duration_ms == 2.0
        assert updated.max_duration_ms == 2.0

    def test_record_single_failure(self) -> None:
        """Recording one failing validation increments failure counter."""
        m = ModelEnvelopeValidationTimingMetrics()
        updated = m.record_validation(total_duration_ms=0.5, passed=False)

        assert updated.total_validations == 1
        assert updated.passed_validations == 0
        assert updated.failed_validations == 1

    def test_immutability(self) -> None:
        """record_validation does not mutate the original instance."""
        original = ModelEnvelopeValidationTimingMetrics()
        _ = original.record_validation(total_duration_ms=1.0, passed=True)
        assert original.total_validations == 0

    def test_min_max_update(self) -> None:
        """Min and max latency track correctly across multiple observations."""
        m = ModelEnvelopeValidationTimingMetrics()
        m = m.record_validation(total_duration_ms=5.0, passed=True)
        m = m.record_validation(total_duration_ms=1.0, passed=True)
        m = m.record_validation(total_duration_ms=10.0, passed=False)

        assert m.min_duration_ms == 1.0
        assert m.max_duration_ms == 10.0

    def test_avg_duration(self) -> None:
        """Average latency is computed correctly from totals."""
        m = ModelEnvelopeValidationTimingMetrics()
        m = m.record_validation(total_duration_ms=2.0, passed=True)
        m = m.record_validation(total_duration_ms=4.0, passed=True)

        assert m.avg_duration_ms == pytest.approx(3.0)

    def test_pass_and_failure_rates(self) -> None:
        """Pass and failure rates are computed from accumulated counts."""
        m = ModelEnvelopeValidationTimingMetrics()
        for _ in range(3):
            m = m.record_validation(total_duration_ms=1.0, passed=True)
        m = m.record_validation(total_duration_ms=1.0, passed=False)

        assert m.pass_rate == pytest.approx(0.75)
        assert m.failure_rate == pytest.approx(0.25)

    def test_step_durations_accumulated(self) -> None:
        """Per-step durations are accumulated across observations."""
        m = ModelEnvelopeValidationTimingMetrics()
        m = m.record_validation(
            total_duration_ms=2.0,
            passed=True,
            step_durations_ms={"correlation_id": 1.0, "envelope_structure": 0.5},
        )
        m = m.record_validation(
            total_duration_ms=3.0,
            passed=True,
            step_durations_ms={"correlation_id": 1.5},
        )

        assert m.step_totals_ms["correlation_id"] == pytest.approx(2.5)
        assert m.step_counts["correlation_id"] == 2
        assert m.step_totals_ms["envelope_structure"] == pytest.approx(0.5)
        assert m.step_counts["envelope_structure"] == 1

    def test_get_step_avg_ms(self) -> None:
        """get_step_avg_ms returns average latency for a named step."""
        m = ModelEnvelopeValidationTimingMetrics()
        m = m.record_validation(
            total_duration_ms=1.0,
            passed=True,
            step_durations_ms={"payload_presence": 0.4},
        )
        m = m.record_validation(
            total_duration_ms=1.0,
            passed=True,
            step_durations_ms={"payload_presence": 0.6},
        )

        result = m.get_step_avg_ms("payload_presence")
        assert result == pytest.approx(0.5)

    def test_get_step_avg_ms_unknown_step(self) -> None:
        """get_step_avg_ms returns None for a step that has not been observed."""
        m = ModelEnvelopeValidationTimingMetrics()
        assert m.get_step_avg_ms("nonexistent_step") is None

    def test_last_recorded_at_updated(self) -> None:
        """last_recorded_at is set after recording a validation."""
        m = ModelEnvelopeValidationTimingMetrics()
        assert m.last_recorded_at is None
        updated = m.record_validation(total_duration_ms=1.0, passed=True)
        assert updated.last_recorded_at is not None


class TestModelEnvelopeValidationTimingMetricsHistogram:
    """Tests for histogram bucket assignment."""

    @pytest.mark.parametrize(
        ("duration_ms", "expected_bucket"),
        [
            (0.05, "le_0_1ms"),
            (0.1, "le_0_1ms"),
            (0.2, "le_0_25ms"),
            (0.25, "le_0_25ms"),
            (0.4, "le_0_5ms"),
            (0.5, "le_0_5ms"),
            (0.8, "le_1ms"),
            (1.0, "le_1ms"),
            (2.0, "le_2_5ms"),
            (5.0, "le_5ms"),
            (8.0, "le_10ms"),
            (20.0, "le_25ms"),
            (40.0, "le_50ms"),
            (80.0, "le_100ms"),
            (150.0, "gt_100ms"),
        ],
    )
    def test_histogram_bucket_assignment(
        self, duration_ms: float, expected_bucket: str
    ) -> None:
        """Latency values are assigned to correct histogram buckets."""
        m = ModelEnvelopeValidationTimingMetrics()
        m = m.record_validation(total_duration_ms=duration_ms, passed=True)
        assert m.latency_histogram[expected_bucket] == 1


class TestModelEnvelopeValidationTimingMetricsPercentiles:
    """Tests for p50/p95/p99 percentile estimation."""

    def test_p50_single_observation(self) -> None:
        """p50 with a single sub-1ms observation falls in le_1ms bucket."""
        m = ModelEnvelopeValidationTimingMetrics()
        m = m.record_validation(total_duration_ms=0.8, passed=True)
        # Falls in le_1ms bucket, upper bound 1.0
        assert m.p50_duration_ms == pytest.approx(1.0)

    def test_p95_all_fast(self) -> None:
        """p95 from 20 sub-millisecond observations stays in low bucket."""
        m = ModelEnvelopeValidationTimingMetrics()
        for _ in range(20):
            m = m.record_validation(total_duration_ms=0.05, passed=True)
        # 19th item (p95 of 20) is still in le_0_1ms bucket
        assert m.p95_duration_ms == pytest.approx(0.1)

    def test_p99_requires_tail(self) -> None:
        """p99 detects tail latency when 1% of values are slow."""
        m = ModelEnvelopeValidationTimingMetrics()
        # 99 fast observations
        for _ in range(99):
            m = m.record_validation(total_duration_ms=0.5, passed=True)
        # 1 slow observation at 50ms
        m = m.record_validation(total_duration_ms=50.0, passed=True)

        # p99 target count = 99; the 99th item is a fast 0.5ms → le_0_5ms bucket
        assert m.p99_duration_ms == pytest.approx(0.5)

    def test_percentiles_none_when_empty(self) -> None:
        """All percentile estimates return None when no observations."""
        m = ModelEnvelopeValidationTimingMetrics()
        assert m.p50_duration_ms is None
        assert m.p95_duration_ms is None
        assert m.p99_duration_ms is None


class TestModelEnvelopeValidationTimingMetricsToDict:
    """Tests for to_dict() serialization."""

    def test_to_dict_keys(self) -> None:
        """to_dict() returns all expected keys."""
        m = ModelEnvelopeValidationTimingMetrics()
        result = m.to_dict()
        expected_keys = {
            "total_validations",
            "passed_validations",
            "failed_validations",
            "avg_duration_ms",
            "min_duration_ms",
            "max_duration_ms",
            "p50_duration_ms",
            "p95_duration_ms",
            "p99_duration_ms",
            "pass_rate",
            "failure_rate",
            "total_duration_ms",
            "latency_histogram",
            "step_totals_ms",
            "step_counts",
            "last_recorded_at",
        }
        assert set(result.keys()) == expected_keys

    def test_histogram_bucket_constant(self) -> None:
        """VALIDATION_LATENCY_HISTOGRAM_BUCKETS has expected length."""
        assert len(VALIDATION_LATENCY_HISTOGRAM_BUCKETS) == 10
