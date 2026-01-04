# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelLatencyStatistics.

Tests latency comparison statistics between baseline and replay executions.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.errors import ModelOnexError
from omnibase_core.models.evidence.model_latency_statistics import (
    ModelLatencyStatistics,
)


@pytest.mark.unit
class TestLatencyStatisticsCreation:
    """Test model instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Create model with all required fields."""
        stats = ModelLatencyStatistics(
            baseline_avg_ms=100.0,
            baseline_p50_ms=95.0,
            baseline_p95_ms=150.0,
            replay_avg_ms=120.0,
            replay_p50_ms=115.0,
            replay_p95_ms=180.0,
            delta_avg_ms=20.0,
            delta_avg_percent=20.0,
            delta_p50_percent=21.05,
            delta_p95_percent=20.0,
        )

        assert stats.baseline_avg_ms == 100.0
        assert stats.baseline_p50_ms == 95.0
        assert stats.baseline_p95_ms == 150.0
        assert stats.replay_avg_ms == 120.0
        assert stats.replay_p50_ms == 115.0
        assert stats.replay_p95_ms == 180.0
        assert stats.delta_avg_ms == 20.0
        assert stats.delta_avg_percent == 20.0
        assert stats.delta_p50_percent == 21.05
        assert stats.delta_p95_percent == 20.0

    def test_immutable_after_creation(self) -> None:
        """Model should be frozen (immutable)."""
        stats = ModelLatencyStatistics(
            baseline_avg_ms=100.0,
            baseline_p50_ms=95.0,
            baseline_p95_ms=150.0,
            replay_avg_ms=120.0,
            replay_p50_ms=115.0,
            replay_p95_ms=180.0,
            delta_avg_ms=20.0,
            delta_avg_percent=20.0,
            delta_p50_percent=21.05,
            delta_p95_percent=20.0,
        )

        with pytest.raises(ValidationError):
            stats.baseline_avg_ms = 200.0  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields should be forbidden."""
        with pytest.raises(ValidationError):
            ModelLatencyStatistics(
                baseline_avg_ms=100.0,
                baseline_p50_ms=95.0,
                baseline_p95_ms=150.0,
                replay_avg_ms=120.0,
                replay_p50_ms=115.0,
                replay_p95_ms=180.0,
                delta_avg_ms=20.0,
                delta_avg_percent=20.0,
                delta_p50_percent=21.05,
                delta_p95_percent=20.0,
                extra_field="not allowed",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestDeltaCalculations:
    """Test delta percentage calculations."""

    def test_delta_avg_percent_positive_regression(self) -> None:
        """Positive delta when replay is slower."""
        # baseline_avg=100, replay_avg=120 -> delta_avg_percent=20.0
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[100.0],
            replay_values=[120.0],
        )

        assert stats.delta_avg_percent == pytest.approx(20.0, rel=0.01)

    def test_delta_avg_percent_negative_improvement(self) -> None:
        """Negative delta when replay is faster."""
        # baseline_avg=100, replay_avg=80 -> delta_avg_percent=-20.0
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[100.0],
            replay_values=[80.0],
        )

        assert stats.delta_avg_percent == pytest.approx(-20.0, rel=0.01)

    def test_delta_p50_percent_calculation(self) -> None:
        """P50 delta calculated correctly."""
        # baseline_p50=100, replay_p50=150 -> delta_p50_percent=50.0
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[100.0],
            replay_values=[150.0],
        )

        assert stats.delta_p50_percent == pytest.approx(50.0, rel=0.01)

    def test_delta_p95_percent_calculation(self) -> None:
        """P95 delta calculated correctly."""
        # Use multiple values so p95 is meaningful
        # baseline: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100] -> p95 ~ 100
        # replay: [20, 40, 60, 80, 100, 120, 140, 160, 180, 200] -> p95 ~ 200
        baseline = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        replay = [20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 180.0, 200.0]

        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=baseline,
            replay_values=replay,
        )

        # p95 of baseline is 100, p95 of replay is 200
        # delta = (200 - 100) / 100 * 100 = 100%
        assert stats.delta_p95_percent == pytest.approx(100.0, rel=0.01)

    def test_delta_with_zero_baseline_handles_gracefully(self) -> None:
        """Handle zero baseline without division error."""
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[0.0],
            replay_values=[100.0],
        )

        # When baseline is zero, delta percent should be 0.0 (graceful handling)
        assert stats.delta_avg_percent == 0.0
        assert stats.delta_p50_percent == 0.0
        assert stats.delta_p95_percent == 0.0

    def test_delta_with_both_zero_handles_gracefully(self) -> None:
        """Handle both baseline and replay zero without division error."""
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[0.0],
            replay_values=[0.0],
        )

        assert stats.delta_avg_percent == 0.0
        assert stats.delta_p50_percent == 0.0
        assert stats.delta_p95_percent == 0.0


@pytest.mark.unit
class TestFromLatencyValues:
    """Test factory method for computing stats from raw values."""

    def test_from_latency_values_computes_avg(self) -> None:
        """Average calculated from raw latency values."""
        # baseline: [100, 200, 300] -> avg = 200
        # replay: [150, 250, 350] -> avg = 250
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[100.0, 200.0, 300.0],
            replay_values=[150.0, 250.0, 350.0],
        )

        assert stats.baseline_avg_ms == pytest.approx(200.0, rel=0.01)
        assert stats.replay_avg_ms == pytest.approx(250.0, rel=0.01)

    def test_from_latency_values_computes_p50_odd_count(self) -> None:
        """P50 (median) calculated correctly - odd count."""
        # [10, 20, 30, 40, 50] -> p50 = 30 (middle element)
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[10.0, 20.0, 30.0, 40.0, 50.0],
            replay_values=[10.0, 20.0, 30.0, 40.0, 50.0],
        )

        assert stats.baseline_p50_ms == pytest.approx(30.0, rel=0.01)

    def test_from_latency_values_computes_p50_even_count(self) -> None:
        """P50 (median) calculated correctly - even count."""
        # [10, 20, 30, 40] -> p50 = 25 (average of 20 and 30)
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[10.0, 20.0, 30.0, 40.0],
            replay_values=[10.0, 20.0, 30.0, 40.0],
        )

        assert stats.baseline_p50_ms == pytest.approx(25.0, rel=0.01)

    def test_from_latency_values_computes_p95(self) -> None:
        """P95 calculated using nearest-rank method."""
        # 20 values: [1, 2, 3, ..., 20]
        # p95 = value at index ceil(0.95 * 20) - 1 = ceil(19) - 1 = 18
        # values[18] = 19
        values = [float(i) for i in range(1, 21)]

        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=values,
            replay_values=values,
        )

        assert stats.baseline_p95_ms == pytest.approx(19.0, rel=0.01)

    def test_from_latency_values_empty_list_raises(self) -> None:
        """Empty latency list raises ModelOnexError."""
        with pytest.raises(ModelOnexError, match="cannot be empty"):
            ModelLatencyStatistics.from_latency_values(
                baseline_values=[],
                replay_values=[100.0],
            )

        with pytest.raises(ModelOnexError, match="cannot be empty"):
            ModelLatencyStatistics.from_latency_values(
                baseline_values=[100.0],
                replay_values=[],
            )

    def test_from_latency_values_length_mismatch_raises(self) -> None:
        """Different length lists raise ModelOnexError."""
        with pytest.raises(ModelOnexError, match="must have the same length"):
            ModelLatencyStatistics.from_latency_values(
                baseline_values=[100.0, 200.0],
                replay_values=[100.0],
            )

    def test_from_latency_values_single_value(self) -> None:
        """Single value: avg=p50=p95=value."""
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[42.0],
            replay_values=[84.0],
        )

        assert stats.baseline_avg_ms == pytest.approx(42.0, rel=0.01)
        assert stats.baseline_p50_ms == pytest.approx(42.0, rel=0.01)
        assert stats.baseline_p95_ms == pytest.approx(42.0, rel=0.01)
        assert stats.replay_avg_ms == pytest.approx(84.0, rel=0.01)
        assert stats.replay_p50_ms == pytest.approx(84.0, rel=0.01)
        assert stats.replay_p95_ms == pytest.approx(84.0, rel=0.01)


@pytest.mark.unit
class TestFromLatencyValuesEdgeCases:
    """Test edge cases for the factory method."""

    def test_unordered_values_sorted_for_percentiles(self) -> None:
        """Values should be sorted internally for correct percentile calculation."""
        # Unordered input: [50, 10, 30, 40, 20]
        # Sorted: [10, 20, 30, 40, 50] -> p50 = 30
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[50.0, 10.0, 30.0, 40.0, 20.0],
            replay_values=[50.0, 10.0, 30.0, 40.0, 20.0],
        )

        assert stats.baseline_p50_ms == pytest.approx(30.0, rel=0.01)

    def test_negative_latency_values_allowed(self) -> None:
        """Negative values are technically allowed (unusual but valid)."""
        # This might happen with time drift or measurement errors
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[-10.0, 0.0, 10.0],
            replay_values=[0.0, 10.0, 20.0],
        )

        assert stats.baseline_avg_ms == pytest.approx(0.0, rel=0.01)
        assert stats.replay_avg_ms == pytest.approx(10.0, rel=0.01)

    def test_very_large_values(self) -> None:
        """Handle very large latency values."""
        large_value = 1e12  # 1 trillion ms
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[large_value],
            replay_values=[large_value * 2],
        )

        assert stats.baseline_avg_ms == pytest.approx(large_value, rel=0.01)
        assert stats.replay_avg_ms == pytest.approx(large_value * 2, rel=0.01)
        assert stats.delta_avg_percent == pytest.approx(100.0, rel=0.01)

    def test_very_small_values(self) -> None:
        """Handle very small (sub-millisecond) latency values."""
        small_value = 0.001  # 1 microsecond
        stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=[small_value],
            replay_values=[small_value * 2],
        )

        assert stats.baseline_avg_ms == pytest.approx(small_value, rel=0.01)
        assert stats.delta_avg_percent == pytest.approx(100.0, rel=0.01)


@pytest.mark.unit
class TestSerialization:
    """Test model serialization."""

    def test_model_dump(self) -> None:
        """Model can be dumped to dictionary."""
        stats = ModelLatencyStatistics(
            baseline_avg_ms=100.0,
            baseline_p50_ms=95.0,
            baseline_p95_ms=150.0,
            replay_avg_ms=120.0,
            replay_p50_ms=115.0,
            replay_p95_ms=180.0,
            delta_avg_ms=20.0,
            delta_avg_percent=20.0,
            delta_p50_percent=21.05,
            delta_p95_percent=20.0,
        )

        dumped = stats.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["baseline_avg_ms"] == 100.0
        assert dumped["delta_avg_percent"] == 20.0

    def test_model_dump_json(self) -> None:
        """Model can be serialized to JSON."""
        stats = ModelLatencyStatistics(
            baseline_avg_ms=100.0,
            baseline_p50_ms=95.0,
            baseline_p95_ms=150.0,
            replay_avg_ms=120.0,
            replay_p50_ms=115.0,
            replay_p95_ms=180.0,
            delta_avg_ms=20.0,
            delta_avg_percent=20.0,
            delta_p50_percent=21.05,
            delta_p95_percent=20.0,
        )

        json_str = stats.model_dump_json()

        assert isinstance(json_str, str)
        assert "baseline_avg_ms" in json_str
        assert "100.0" in json_str

    def test_round_trip_serialization(self) -> None:
        """Model can be serialized and deserialized."""
        original = ModelLatencyStatistics(
            baseline_avg_ms=100.0,
            baseline_p50_ms=95.0,
            baseline_p95_ms=150.0,
            replay_avg_ms=120.0,
            replay_p50_ms=115.0,
            replay_p95_ms=180.0,
            delta_avg_ms=20.0,
            delta_avg_percent=20.0,
            delta_p50_percent=21.05,
            delta_p95_percent=20.0,
        )

        dumped = original.model_dump()
        restored = ModelLatencyStatistics(**dumped)

        assert restored.baseline_avg_ms == original.baseline_avg_ms
        assert restored.delta_avg_percent == original.delta_avg_percent
