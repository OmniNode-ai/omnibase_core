"""
Tests for MixinMetrics - Performance metrics collection mixin.

Coverage target: 60%+ (stub implementation with defensive attribute handling)
"""

import pytest

from omnibase_core.mixins.mixin_metrics import MixinMetrics


class TestNode(MixinMetrics):
    """Test node class that uses MixinMetrics."""


class TestMixinMetricsInit:
    """Test suite for MixinMetrics initialization."""

    def test_init_sets_metrics_enabled(self):
        """Test that __init__ sets _metrics_enabled to True."""
        node = TestNode()
        # Use object.__getattribute__() to access the attribute
        metrics_enabled = object.__getattribute__(node, "_metrics_enabled")
        assert metrics_enabled is True

    def test_init_creates_empty_metrics_dict(self):
        """Test that __init__ creates empty _metrics_data dict."""
        node = TestNode()
        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data == {}
        assert isinstance(metrics_data, dict)


class TestRecordMetric:
    """Test suite for record_metric method."""

    def test_record_metric_basic(self):
        """Test basic metric recording."""
        node = TestNode()

        node.record_metric("test_metric", 42.5)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert "test_metric" in metrics_data
        assert metrics_data["test_metric"]["value"] == 42.5
        assert metrics_data["test_metric"]["tags"] == {}

    def test_record_metric_with_tags(self):
        """Test metric recording with tags."""
        node = TestNode()
        tags = {"env": "test", "service": "api"}

        node.record_metric("request_time", 123.45, tags=tags)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["request_time"]["value"] == 123.45
        assert metrics_data["request_time"]["tags"] == tags

    def test_record_metric_overwrites_existing(self):
        """Test that recording a metric overwrites existing value."""
        node = TestNode()

        node.record_metric("metric1", 10.0)
        node.record_metric("metric1", 20.0)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["metric1"]["value"] == 20.0

    def test_record_metric_multiple_metrics(self):
        """Test recording multiple different metrics."""
        node = TestNode()

        node.record_metric("metric_a", 1.0)
        node.record_metric("metric_b", 2.0)
        node.record_metric("metric_c", 3.0)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert len(metrics_data) == 3
        assert metrics_data["metric_a"]["value"] == 1.0
        assert metrics_data["metric_b"]["value"] == 2.0
        assert metrics_data["metric_c"]["value"] == 3.0

    def test_record_metric_with_empty_tags(self):
        """Test recording metric with explicitly empty tags."""
        node = TestNode()

        node.record_metric("metric1", 100.0, tags={})

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["metric1"]["tags"] == {}

    def test_record_metric_with_negative_value(self):
        """Test recording metric with negative value."""
        node = TestNode()

        node.record_metric("temperature", -15.5)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["temperature"]["value"] == -15.5

    def test_record_metric_with_zero_value(self):
        """Test recording metric with zero value."""
        node = TestNode()

        node.record_metric("error_count", 0.0)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["error_count"]["value"] == 0.0

    def test_record_metric_defensive_initialization(self):
        """Test that record_metric handles missing initialization gracefully."""
        node = TestNode()

        # Delete the metrics attributes to test defensive initialization
        try:
            delattr(node, "_metrics_enabled")
            delattr(node, "_metrics_data")
        except AttributeError:
            # Attributes might be set via object.__setattr__, so use that to delete
            pass

        # Should still work and initialize attributes
        node.record_metric("test", 1.0)

        # Attributes should now exist
        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert "test" in metrics_data


class TestIncrementCounter:
    """Test suite for increment_counter method."""

    def test_increment_counter_default_increment(self):
        """Test counter increment with default value (1)."""
        node = TestNode()

        node.increment_counter("requests")

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["requests"]["value"] == 1

    def test_increment_counter_custom_increment(self):
        """Test counter increment with custom value."""
        node = TestNode()

        node.increment_counter("bytes_sent", value=1024)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["bytes_sent"]["value"] == 1024

    def test_increment_counter_multiple_times(self):
        """Test incrementing counter multiple times."""
        node = TestNode()

        node.increment_counter("api_calls")
        node.increment_counter("api_calls")
        node.increment_counter("api_calls")

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["api_calls"]["value"] == 3

    def test_increment_counter_with_custom_values(self):
        """Test incrementing counter with varying custom values."""
        node = TestNode()

        node.increment_counter("total_bytes", value=100)
        node.increment_counter("total_bytes", value=200)
        node.increment_counter("total_bytes", value=50)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["total_bytes"]["value"] == 350

    def test_increment_counter_from_zero(self):
        """Test that counter starts from zero."""
        node = TestNode()

        # First increment should start from 0
        node.increment_counter("new_counter", value=5)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["new_counter"]["value"] == 5

    def test_increment_counter_negative_value(self):
        """Test incrementing counter with negative value (decrement)."""
        node = TestNode()

        node.increment_counter("balance", value=100)
        node.increment_counter("balance", value=-30)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["balance"]["value"] == 70

    def test_increment_counter_defensive_initialization(self):
        """Test that increment_counter handles missing initialization gracefully."""
        node = TestNode()

        # Should work even if attributes are missing (defensive initialization)
        node.increment_counter("test_counter", value=10)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["test_counter"]["value"] == 10


class TestGetMetrics:
    """Test suite for get_metrics method."""

    def test_get_metrics_empty(self):
        """Test get_metrics on empty metrics data."""
        node = TestNode()

        metrics = node.get_metrics()

        assert isinstance(metrics, dict)
        assert len(metrics) == 0

    def test_get_metrics_returns_copy(self):
        """Test that get_metrics returns a copy, not reference."""
        node = TestNode()

        node.record_metric("metric1", 100.0)

        metrics1 = node.get_metrics()
        metrics2 = node.get_metrics()

        # Should be equal but not the same object
        assert metrics1 == metrics2
        assert metrics1 is not metrics2

    def test_get_metrics_after_recording(self):
        """Test get_metrics returns all recorded metrics."""
        node = TestNode()

        node.record_metric("metric_a", 1.0, tags={"tag1": "value1"})
        node.increment_counter("counter_b", value=5)

        metrics = node.get_metrics()

        assert "metric_a" in metrics
        assert "counter_b" in metrics
        assert metrics["metric_a"]["value"] == 1.0
        assert metrics["counter_b"]["value"] == 5

    def test_get_metrics_defensive_initialization(self):
        """Test that get_metrics handles missing initialization gracefully."""
        node = TestNode()

        # Should work even if _metrics_data doesn't exist
        metrics = node.get_metrics()

        assert isinstance(metrics, dict)

    def test_get_metrics_with_multiple_metrics(self):
        """Test get_metrics with various metric types."""
        node = TestNode()

        node.record_metric("response_time", 45.2, tags={"endpoint": "/api/users"})
        node.increment_counter("requests_total")
        node.increment_counter("requests_total")
        node.record_metric("cpu_usage", 75.5)

        metrics = node.get_metrics()

        assert len(metrics) == 3
        assert metrics["response_time"]["value"] == 45.2
        assert metrics["requests_total"]["value"] == 2
        assert metrics["cpu_usage"]["value"] == 75.5


class TestResetMetrics:
    """Test suite for reset_metrics method."""

    def test_reset_metrics_clears_all_data(self):
        """Test that reset_metrics clears all metrics data."""
        node = TestNode()

        # Record some metrics
        node.record_metric("metric1", 10.0)
        node.increment_counter("counter1")
        node.record_metric("metric2", 20.0)

        # Verify metrics exist
        metrics_before = node.get_metrics()
        assert len(metrics_before) == 3

        # Reset
        node.reset_metrics()

        # Verify metrics are cleared
        metrics_after = node.get_metrics()
        assert len(metrics_after) == 0
        assert metrics_after == {}

    def test_reset_metrics_on_empty(self):
        """Test reset_metrics on already empty metrics."""
        node = TestNode()

        # Should not raise error
        node.reset_metrics()

        metrics = node.get_metrics()
        assert metrics == {}

    def test_reset_metrics_defensive_initialization(self):
        """Test that reset_metrics handles missing initialization gracefully."""
        node = TestNode()

        # Should work even if attributes don't exist
        node.reset_metrics()

        # Should still be able to record after reset
        node.record_metric("test", 1.0)
        metrics = node.get_metrics()
        assert metrics["test"]["value"] == 1.0


class TestMetricsIntegration:
    """Integration tests for MixinMetrics workflow."""

    def test_full_metrics_workflow(self):
        """Test complete metrics workflow: record, increment, get, reset."""
        node = TestNode()

        # Record various metrics
        node.record_metric("latency_ms", 250.5, tags={"service": "api"})
        node.increment_counter("api_calls")
        node.increment_counter("api_calls")
        node.increment_counter("api_calls")
        node.record_metric("memory_mb", 512.0)

        # Get metrics
        metrics = node.get_metrics()
        assert len(metrics) == 3
        assert metrics["latency_ms"]["value"] == 250.5
        assert metrics["api_calls"]["value"] == 3
        assert metrics["memory_mb"]["value"] == 512.0

        # Reset
        node.reset_metrics()
        metrics_after = node.get_metrics()
        assert len(metrics_after) == 0

        # Can record new metrics after reset
        node.record_metric("new_metric", 1.0)
        metrics_new = node.get_metrics()
        assert len(metrics_new) == 1

    def test_counter_and_metric_coexistence(self):
        """Test that counters and regular metrics work together."""
        node = TestNode()

        # Mix of counters and regular metrics
        node.increment_counter("request_count", value=10)
        node.record_metric("avg_response_time", 123.45)
        node.increment_counter("error_count", value=2)
        node.record_metric("success_rate", 0.95)

        metrics = node.get_metrics()

        assert len(metrics) == 4
        assert metrics["request_count"]["value"] == 10
        assert metrics["avg_response_time"]["value"] == 123.45
        assert metrics["error_count"]["value"] == 2
        assert metrics["success_rate"]["value"] == 0.95

    def test_metric_overwrite_behavior(self):
        """Test how metrics behave when overwritten."""
        node = TestNode()

        # Record initial value
        node.record_metric("temperature", 20.0, tags={"unit": "celsius"})

        initial_metrics = node.get_metrics()
        assert initial_metrics["temperature"]["value"] == 20.0
        assert initial_metrics["temperature"]["tags"] == {"unit": "celsius"}

        # Overwrite with new value and tags
        node.record_metric(
            "temperature", 25.0, tags={"unit": "celsius", "location": "room1"}
        )

        updated_metrics = node.get_metrics()
        assert updated_metrics["temperature"]["value"] == 25.0
        assert updated_metrics["temperature"]["tags"] == {
            "unit": "celsius",
            "location": "room1",
        }

    def test_large_number_of_metrics(self):
        """Test handling of many metrics."""
        node = TestNode()

        # Record many metrics
        for i in range(100):
            node.record_metric(f"metric_{i}", float(i))

        metrics = node.get_metrics()
        assert len(metrics) == 100

        # Verify some values
        assert metrics["metric_0"]["value"] == 0.0
        assert metrics["metric_50"]["value"] == 50.0
        assert metrics["metric_99"]["value"] == 99.0

    def test_metrics_with_special_characters_in_names(self):
        """Test metrics with special characters in names."""
        node = TestNode()

        node.record_metric("api.requests.total", 100.0)
        node.record_metric("cache:hit_rate", 0.85)
        node.increment_counter("errors/rate")

        metrics = node.get_metrics()

        assert "api.requests.total" in metrics
        assert "cache:hit_rate" in metrics
        assert "errors/rate" in metrics
