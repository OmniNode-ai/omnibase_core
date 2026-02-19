# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelPerformanceMetrics."""

import pytest
from pydantic import ValidationError

from omnibase_core.errors import ModelOnexError
from omnibase_core.models.health.model_performance_metrics import (
    ModelPerformanceMetrics,
)


@pytest.mark.unit
class TestModelPerformanceMetricsBasics:
    """Test basic functionality."""

    def test_basic_initialization(self):
        """Test basic metrics initialization."""
        metrics = ModelPerformanceMetrics(
            avg_latency_ms=150.5,
            p95_latency_ms=450.0,
            p99_latency_ms=800.0,
            avg_cost_per_call=0.002,
            total_calls=10000,
            error_rate=0.01,
        )

        assert metrics.avg_latency_ms == 150.5
        assert metrics.p95_latency_ms == 450.0
        assert metrics.p99_latency_ms == 800.0
        assert metrics.avg_cost_per_call == 0.002
        assert metrics.total_calls == 10000
        assert metrics.error_rate == 0.01

    def test_frozen_model(self):
        """Test that model is frozen (immutable)."""
        metrics = ModelPerformanceMetrics(
            avg_latency_ms=100.0,
            p95_latency_ms=200.0,
            p99_latency_ms=300.0,
            avg_cost_per_call=0.001,
            total_calls=1000,
            error_rate=0.05,
        )

        with pytest.raises(ValidationError):  # Pydantic frozen model raises
            metrics.avg_latency_ms = 200.0


@pytest.mark.unit
class TestModelPerformanceMetricsPercentileValidation:
    """Test percentile ordering validation."""

    def test_valid_percentile_ordering(self):
        """Test that valid percentile ordering passes validation."""
        # avg < p95 < p99
        metrics = ModelPerformanceMetrics(
            avg_latency_ms=100.0,
            p95_latency_ms=200.0,
            p99_latency_ms=300.0,
            avg_cost_per_call=0.001,
            total_calls=1000,
            error_rate=0.01,
        )
        assert metrics.avg_latency_ms == 100.0
        assert metrics.p95_latency_ms == 200.0
        assert metrics.p99_latency_ms == 300.0

    def test_equal_percentiles_valid(self):
        """Test that equal percentiles are valid (edge case)."""
        # All equal is valid (avg <= p95 <= p99)
        metrics = ModelPerformanceMetrics(
            avg_latency_ms=100.0,
            p95_latency_ms=100.0,
            p99_latency_ms=100.0,
            avg_cost_per_call=0.001,
            total_calls=1000,
            error_rate=0.01,
        )
        assert metrics.avg_latency_ms == 100.0
        assert metrics.p95_latency_ms == 100.0
        assert metrics.p99_latency_ms == 100.0

    def test_avg_equals_p95_less_than_p99(self):
        """Test avg == p95 < p99 is valid."""
        metrics = ModelPerformanceMetrics(
            avg_latency_ms=100.0,
            p95_latency_ms=100.0,
            p99_latency_ms=200.0,
            avg_cost_per_call=0.001,
            total_calls=1000,
            error_rate=0.01,
        )
        assert metrics.avg_latency_ms == 100.0
        assert metrics.p95_latency_ms == 100.0
        assert metrics.p99_latency_ms == 200.0

    def test_avg_less_than_p95_equals_p99(self):
        """Test avg < p95 == p99 is valid."""
        metrics = ModelPerformanceMetrics(
            avg_latency_ms=100.0,
            p95_latency_ms=200.0,
            p99_latency_ms=200.0,
            avg_cost_per_call=0.001,
            total_calls=1000,
            error_rate=0.01,
        )
        assert metrics.avg_latency_ms == 100.0
        assert metrics.p95_latency_ms == 200.0
        assert metrics.p99_latency_ms == 200.0

    def test_invalid_avg_greater_than_p95(self):
        """Test that avg > p95 raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPerformanceMetrics(
                avg_latency_ms=300.0,  # avg > p95
                p95_latency_ms=200.0,
                p99_latency_ms=400.0,
                avg_cost_per_call=0.001,
                total_calls=1000,
                error_rate=0.01,
            )

        assert "Latency percentiles must be ordered" in str(exc_info.value)
        assert exc_info.value.context is not None
        # Context is nested in additional_context.context
        ctx = exc_info.value.context["additional_context"]["context"]
        assert ctx["avg_latency_ms"] == 300.0
        assert ctx["p95_latency_ms"] == 200.0
        assert ctx["p99_latency_ms"] == 400.0

    def test_invalid_p95_greater_than_p99(self):
        """Test that p95 > p99 raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPerformanceMetrics(
                avg_latency_ms=100.0,
                p95_latency_ms=400.0,  # p95 > p99
                p99_latency_ms=300.0,
                avg_cost_per_call=0.001,
                total_calls=1000,
                error_rate=0.01,
            )

        assert "Latency percentiles must be ordered" in str(exc_info.value)
        assert exc_info.value.context is not None
        # Context is nested in additional_context.context
        ctx = exc_info.value.context["additional_context"]["context"]
        assert ctx["avg_latency_ms"] == 100.0
        assert ctx["p95_latency_ms"] == 400.0
        assert ctx["p99_latency_ms"] == 300.0

    def test_invalid_avg_greater_than_p99(self):
        """Test that avg > p99 raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPerformanceMetrics(
                avg_latency_ms=500.0,  # avg > p99
                p95_latency_ms=400.0,
                p99_latency_ms=300.0,
                avg_cost_per_call=0.001,
                total_calls=1000,
                error_rate=0.01,
            )

        assert "Latency percentiles must be ordered" in str(exc_info.value)

    def test_zero_latencies_valid(self):
        """Test that zero latencies are valid."""
        metrics = ModelPerformanceMetrics(
            avg_latency_ms=0.0,
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
            avg_cost_per_call=0.0,
            total_calls=0,
            error_rate=0.0,
        )
        assert metrics.avg_latency_ms == 0.0
        assert metrics.p95_latency_ms == 0.0
        assert metrics.p99_latency_ms == 0.0


@pytest.mark.unit
class TestModelPerformanceMetricsFieldValidation:
    """Test field-level validation."""

    def test_negative_latency_rejected(self):
        """Test that negative latency values are rejected."""
        with pytest.raises(ValidationError):  # Pydantic validation error
            ModelPerformanceMetrics(
                avg_latency_ms=-1.0,
                p95_latency_ms=200.0,
                p99_latency_ms=300.0,
                avg_cost_per_call=0.001,
                total_calls=1000,
                error_rate=0.01,
            )

    def test_error_rate_bounds(self):
        """Test that error_rate is bounded between 0 and 1."""
        # Valid: error_rate = 0
        metrics = ModelPerformanceMetrics(
            avg_latency_ms=100.0,
            p95_latency_ms=200.0,
            p99_latency_ms=300.0,
            avg_cost_per_call=0.001,
            total_calls=1000,
            error_rate=0.0,
        )
        assert metrics.error_rate == 0.0

        # Valid: error_rate = 1
        metrics = ModelPerformanceMetrics(
            avg_latency_ms=100.0,
            p95_latency_ms=200.0,
            p99_latency_ms=300.0,
            avg_cost_per_call=0.001,
            total_calls=1000,
            error_rate=1.0,
        )
        assert metrics.error_rate == 1.0

        # Invalid: error_rate > 1
        with pytest.raises(ValidationError):
            ModelPerformanceMetrics(
                avg_latency_ms=100.0,
                p95_latency_ms=200.0,
                p99_latency_ms=300.0,
                avg_cost_per_call=0.001,
                total_calls=1000,
                error_rate=1.5,
            )

        # Invalid: error_rate < 0
        with pytest.raises(ValidationError):
            ModelPerformanceMetrics(
                avg_latency_ms=100.0,
                p95_latency_ms=200.0,
                p99_latency_ms=300.0,
                avg_cost_per_call=0.001,
                total_calls=1000,
                error_rate=-0.1,
            )

    def test_negative_total_calls_rejected(self):
        """Test that negative total_calls is rejected."""
        with pytest.raises(ValidationError):
            ModelPerformanceMetrics(
                avg_latency_ms=100.0,
                p95_latency_ms=200.0,
                p99_latency_ms=300.0,
                avg_cost_per_call=0.001,
                total_calls=-1,
                error_rate=0.01,
            )
