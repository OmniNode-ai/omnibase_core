"""Tests for ModelHealthMetrics."""

from datetime import UTC, datetime, timedelta

import pytest

from omnibase_core.models.health.model_health_metrics import ModelHealthMetrics


class TestModelHealthMetricsBasics:
    """Test basic ModelHealthMetrics functionality."""

    def test_default_initialization(self):
        """Test default metrics initialization."""
        metrics = ModelHealthMetrics()

        assert metrics.cpu_usage_percent == 0.0
        assert metrics.memory_usage_mb == 0
        assert metrics.memory_usage_percent == 0.0
        assert metrics.response_time_ms == 0.0
        assert metrics.error_rate == 0.0
        assert metrics.success_rate == 100.0
        assert metrics.active_connections == 0
        assert metrics.requests_per_second == 0.0
        assert metrics.uptime_seconds == 0
        assert metrics.last_error_timestamp is None
        assert metrics.consecutive_errors == 0
        assert metrics.health_check_latency_ms is None
        assert metrics.custom_metrics == {}

    def test_custom_initialization(self):
        """Test metrics with custom values."""
        now = datetime.now(UTC)
        metrics = ModelHealthMetrics(
            cpu_usage_percent=45.5,
            memory_usage_mb=2048,
            memory_usage_percent=60.0,
            response_time_ms=150.0,
            error_rate=2.5,
            success_rate=97.5,
            active_connections=25,
            requests_per_second=100.0,
            uptime_seconds=3600,
            last_error_timestamp=now,
            consecutive_errors=2,
            health_check_latency_ms=50.0,
            custom_metrics={"custom_key": "custom_value"},
        )

        assert metrics.cpu_usage_percent == 45.5
        assert metrics.memory_usage_mb == 2048
        assert metrics.memory_usage_percent == 60.0
        assert metrics.response_time_ms == 150.0
        assert metrics.error_rate == 2.5
        assert metrics.success_rate == 97.5
        assert metrics.active_connections == 25
        assert metrics.requests_per_second == 100.0
        assert metrics.uptime_seconds == 3600
        assert metrics.last_error_timestamp == now
        assert metrics.consecutive_errors == 2
        assert metrics.health_check_latency_ms == 50.0
        assert metrics.custom_metrics == {"custom_key": "custom_value"}


class TestModelHealthMetricsValidation:
    """Test ModelHealthMetrics validation."""

    def test_cpu_usage_validation(self):
        """Test CPU usage percentage validation."""
        # Valid values
        ModelHealthMetrics(cpu_usage_percent=0.0)
        ModelHealthMetrics(cpu_usage_percent=50.0)
        ModelHealthMetrics(cpu_usage_percent=100.0)

        # Invalid values
        with pytest.raises(Exception):
            ModelHealthMetrics(cpu_usage_percent=-1.0)
        with pytest.raises(Exception):
            ModelHealthMetrics(cpu_usage_percent=101.0)

    def test_memory_usage_validation(self):
        """Test memory usage validation."""
        # Valid values
        ModelHealthMetrics(memory_usage_mb=0)
        ModelHealthMetrics(memory_usage_mb=1024)
        ModelHealthMetrics(memory_usage_percent=0.0)
        ModelHealthMetrics(memory_usage_percent=100.0)

        # Invalid values
        with pytest.raises(Exception):
            ModelHealthMetrics(memory_usage_mb=-1)
        with pytest.raises(Exception):
            ModelHealthMetrics(memory_usage_percent=-1.0)
        with pytest.raises(Exception):
            ModelHealthMetrics(memory_usage_percent=101.0)

    def test_error_rate_validation(self):
        """Test error rate validation."""
        # Valid values
        ModelHealthMetrics(error_rate=0.0)
        ModelHealthMetrics(error_rate=50.0)
        ModelHealthMetrics(error_rate=100.0)

        # Invalid values
        with pytest.raises(Exception):
            ModelHealthMetrics(error_rate=-1.0)
        with pytest.raises(Exception):
            ModelHealthMetrics(error_rate=101.0)

    def test_success_rate_validation(self):
        """Test success rate validation."""
        # Valid values
        ModelHealthMetrics(success_rate=0.0)
        ModelHealthMetrics(success_rate=50.0)
        ModelHealthMetrics(success_rate=100.0)

        # Invalid values
        with pytest.raises(Exception):
            ModelHealthMetrics(success_rate=-1.0)
        with pytest.raises(Exception):
            ModelHealthMetrics(success_rate=101.0)

    def test_negative_values_validation(self):
        """Test that negative values are rejected."""
        with pytest.raises(Exception):
            ModelHealthMetrics(response_time_ms=-1.0)
        with pytest.raises(Exception):
            ModelHealthMetrics(active_connections=-1)
        with pytest.raises(Exception):
            ModelHealthMetrics(requests_per_second=-1.0)
        with pytest.raises(Exception):
            ModelHealthMetrics(uptime_seconds=-1)
        with pytest.raises(Exception):
            ModelHealthMetrics(consecutive_errors=-1)
        with pytest.raises(Exception):
            ModelHealthMetrics(health_check_latency_ms=-1.0)


class TestModelHealthMetricsHealthChecking:
    """Test health checking logic."""

    def test_is_healthy_default(self):
        """Test is_healthy with default metrics."""
        metrics = ModelHealthMetrics()
        assert metrics.is_healthy() is True

    def test_is_healthy_with_good_metrics(self):
        """Test is_healthy with good metrics."""
        metrics = ModelHealthMetrics(
            cpu_usage_percent=50.0,
            memory_usage_percent=50.0,
            error_rate=5.0,
            consecutive_errors=2,
        )
        assert metrics.is_healthy() is True

    def test_is_healthy_cpu_threshold(self):
        """Test is_healthy with CPU threshold."""
        metrics = ModelHealthMetrics(cpu_usage_percent=95.0)
        assert metrics.is_healthy() is False
        assert metrics.is_healthy(cpu_threshold=96.0) is True

    def test_is_healthy_memory_threshold(self):
        """Test is_healthy with memory threshold."""
        metrics = ModelHealthMetrics(memory_usage_percent=95.0)
        assert metrics.is_healthy() is False
        assert metrics.is_healthy(memory_threshold=96.0) is True

    def test_is_healthy_error_threshold(self):
        """Test is_healthy with error rate threshold."""
        metrics = ModelHealthMetrics(error_rate=15.0)
        assert metrics.is_healthy() is False
        assert metrics.is_healthy(error_threshold=20.0) is True

    def test_is_healthy_consecutive_errors(self):
        """Test is_healthy with consecutive errors."""
        metrics = ModelHealthMetrics(consecutive_errors=5)
        assert metrics.is_healthy() is False

        metrics = ModelHealthMetrics(consecutive_errors=4)
        assert metrics.is_healthy() is True

    def test_is_healthy_custom_status_string(self):
        """Test is_healthy with custom status strings."""
        metrics = ModelHealthMetrics(custom_metrics={"status": "warning"})
        assert metrics.is_healthy() is False

        metrics = ModelHealthMetrics(custom_metrics={"status": "critical"})
        assert metrics.is_healthy() is False

        metrics = ModelHealthMetrics(custom_metrics={"status": "error"})
        assert metrics.is_healthy() is False

        metrics = ModelHealthMetrics(custom_metrics={"status": "healthy"})
        assert metrics.is_healthy() is True

    def test_is_healthy_custom_status_numeric(self):
        """Test is_healthy with custom numeric status."""
        metrics = ModelHealthMetrics(custom_metrics={"status": 0.5})
        assert metrics.is_healthy() is False

        metrics = ModelHealthMetrics(custom_metrics={"status": 1.0})
        assert metrics.is_healthy() is True

        metrics = ModelHealthMetrics(custom_metrics={"status": 1.5})
        assert metrics.is_healthy() is True


class TestModelHealthMetricsHealthScore:
    """Test health score calculation."""

    def test_get_health_score_perfect(self):
        """Test health score with perfect metrics."""
        metrics = ModelHealthMetrics()
        score = metrics.get_health_score()
        assert 0.9 <= score <= 1.0  # Should be near perfect

    def test_get_health_score_high_cpu(self):
        """Test health score with high CPU usage."""
        metrics = ModelHealthMetrics(cpu_usage_percent=90.0)
        score = metrics.get_health_score()
        assert score < 0.9

    def test_get_health_score_high_memory(self):
        """Test health score with high memory usage."""
        metrics = ModelHealthMetrics(memory_usage_percent=90.0)
        score = metrics.get_health_score()
        assert score < 0.9

    def test_get_health_score_high_error_rate(self):
        """Test health score with high error rate."""
        metrics = ModelHealthMetrics(error_rate=50.0)
        score = metrics.get_health_score()
        # Error rate has 30% weight, so 50% error = 0.5 error_score
        # Expected: 0.2 * 1.0 (cpu) + 0.2 * 1.0 (mem) + 0.3 * 0.5 (error) + 0.3 * 1.0 (response) = 0.85
        assert abs(score - 0.85) < 0.01

    def test_get_health_score_slow_response(self):
        """Test health score with slow response time."""
        metrics = ModelHealthMetrics(response_time_ms=2000.0)
        score = metrics.get_health_score()
        assert score < 0.8

    def test_get_health_score_consecutive_errors_penalty(self):
        """Test health score penalty for consecutive errors."""
        metrics_no_errors = ModelHealthMetrics()
        score_no_errors = metrics_no_errors.get_health_score()

        metrics_with_errors = ModelHealthMetrics(consecutive_errors=3)
        score_with_errors = metrics_with_errors.get_health_score()

        assert score_with_errors < score_no_errors

    def test_get_health_score_bounds(self):
        """Test health score stays within bounds."""
        # Worst case scenario
        metrics = ModelHealthMetrics(
            cpu_usage_percent=100.0,
            memory_usage_percent=100.0,
            error_rate=100.0,
            response_time_ms=10000.0,
            consecutive_errors=10,
        )
        score = metrics.get_health_score()
        assert 0.0 <= score <= 1.0


class TestModelHealthMetricsCustomMetrics:
    """Test custom metrics management."""

    def test_add_custom_metric(self):
        """Test adding custom metrics."""
        metrics = ModelHealthMetrics()
        metrics.add_custom_metric("disk_usage", 75.0)

        assert metrics.custom_metrics["disk_usage"] == 75.0

    def test_update_custom_metric(self):
        """Test updating existing custom metric."""
        metrics = ModelHealthMetrics()
        metrics.add_custom_metric("disk_usage", 75.0)
        metrics.add_custom_metric("disk_usage", 80.0)

        assert metrics.custom_metrics["disk_usage"] == 80.0

    def test_get_custom_metric(self):
        """Test getting custom metric."""
        metrics = ModelHealthMetrics()
        metrics.add_custom_metric("disk_usage", 75.0)

        assert metrics.get_custom_metric("disk_usage") == 75.0

    def test_get_custom_metric_default(self):
        """Test getting non-existent custom metric with default."""
        metrics = ModelHealthMetrics()

        assert metrics.get_custom_metric("nonexistent") == 0.0
        assert metrics.get_custom_metric("nonexistent", 42.0) == 42.0

    def test_multiple_custom_metrics(self):
        """Test managing multiple custom metrics."""
        metrics = ModelHealthMetrics()
        metrics.add_custom_metric("disk_usage", 75.0)
        metrics.add_custom_metric("network_latency", 50.0)
        metrics.add_custom_metric("queue_depth", 10.0)

        assert len(metrics.custom_metrics) == 3
        assert metrics.get_custom_metric("disk_usage") == 75.0
        assert metrics.get_custom_metric("network_latency") == 50.0
        assert metrics.get_custom_metric("queue_depth") == 10.0


class TestModelHealthMetricsStatusProperty:
    """Test status property."""

    def test_status_string_value(self):
        """Test status property with string value."""
        metrics = ModelHealthMetrics(custom_metrics={"status": "healthy"})
        assert metrics.status == "healthy"

    def test_status_numeric_healthy(self):
        """Test status property with numeric healthy value."""
        metrics = ModelHealthMetrics(custom_metrics={"status": 1.0})
        assert metrics.status == "healthy"

        metrics = ModelHealthMetrics(custom_metrics={"status": 1.5})
        assert metrics.status == "healthy"

    def test_status_numeric_warning(self):
        """Test status property with numeric warning value."""
        metrics = ModelHealthMetrics(custom_metrics={"status": 0.5})
        assert metrics.status == "warning"

        metrics = ModelHealthMetrics(custom_metrics={"status": 0.99})
        assert metrics.status == "warning"

    def test_status_numeric_critical(self):
        """Test status property with numeric critical value."""
        metrics = ModelHealthMetrics(custom_metrics={"status": 0.0})
        assert metrics.status == "critical"

        metrics = ModelHealthMetrics(custom_metrics={"status": 0.49})
        assert metrics.status == "critical"

    def test_status_inferred_from_metrics(self):
        """Test status inferred from metrics when not set."""
        # Healthy
        metrics = ModelHealthMetrics()
        assert metrics.status == "healthy"

        # Critical
        metrics = ModelHealthMetrics(error_rate=15.0)
        assert metrics.status == "critical"

        metrics = ModelHealthMetrics(consecutive_errors=5)
        assert metrics.status == "critical"

        # Warning (unhealthy but not critical)
        metrics = ModelHealthMetrics(cpu_usage_percent=95.0)
        assert metrics.status == "warning"


class TestModelHealthMetricsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_values(self):
        """Test metrics with all zero values."""
        metrics = ModelHealthMetrics(
            cpu_usage_percent=0.0,
            memory_usage_mb=0,
            memory_usage_percent=0.0,
            response_time_ms=0.0,
            error_rate=0.0,
            consecutive_errors=0,
        )

        assert metrics.is_healthy() is True
        assert metrics.get_health_score() >= 0.9

    def test_maximum_values(self):
        """Test metrics with maximum values."""
        metrics = ModelHealthMetrics(
            cpu_usage_percent=100.0,
            memory_usage_percent=100.0,
            error_rate=100.0,
            success_rate=0.0,
        )

        assert metrics.is_healthy() is False
        score = metrics.get_health_score()
        assert 0.0 <= score <= 1.0

    def test_timestamp_handling(self):
        """Test timestamp handling."""
        now = datetime.now(UTC)
        past = now - timedelta(hours=1)

        metrics = ModelHealthMetrics(last_error_timestamp=past)
        assert metrics.last_error_timestamp == past

        metrics = ModelHealthMetrics(last_error_timestamp=now)
        assert metrics.last_error_timestamp == now

    def test_custom_metrics_with_various_types(self):
        """Test custom metrics with different value types."""
        metrics = ModelHealthMetrics(
            custom_metrics={
                "string_value": "test",
                "float_value": 42.5,
                "int_value": 100,
                "bool_value": True,
            }
        )

        assert metrics.custom_metrics["string_value"] == "test"
        assert metrics.custom_metrics["float_value"] == 42.5
        assert metrics.custom_metrics["int_value"] == 100
        assert metrics.custom_metrics["bool_value"] is True
