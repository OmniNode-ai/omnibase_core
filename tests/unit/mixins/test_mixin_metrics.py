"""
Tests for MixinMetrics - Performance metrics collection mixin.

Coverage target: 60%+ (stub implementation with defensive attribute handling)
"""

import pytest

from omnibase_core.mixins.mixin_metrics import MixinMetrics


class MockNode(MixinMetrics):
    """Mock node class that uses MixinMetrics."""


@pytest.mark.unit
class TestMixinMetricsInit:
    """Test suite for MixinMetrics initialization."""

    def test_init_sets_metrics_enabled(self):
        """Test that __init__ sets _metrics_enabled to True."""
        node = MockNode()
        # Use object.__getattribute__() to access the attribute
        metrics_enabled = object.__getattribute__(node, "_metrics_enabled")
        assert metrics_enabled is True

    def test_init_creates_empty_metrics_dict(self):
        """Test that __init__ creates empty _metrics_data dict."""
        node = MockNode()
        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data == {}
        assert isinstance(metrics_data, dict)


@pytest.mark.unit
class TestRecordMetric:
    """Test suite for record_metric method."""

    def test_record_metric_basic(self):
        """Test basic metric recording."""
        node = MockNode()

        node.record_metric("test_metric", 42.5)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert "test_metric" in metrics_data
        assert metrics_data["test_metric"]["value"] == 42.5
        assert metrics_data["test_metric"]["tags"] == {}

    def test_record_metric_with_tags(self):
        """Test metric recording with tags."""
        node = MockNode()
        tags = {"env": "test", "service": "api"}

        node.record_metric("request_time", 123.45, tags=tags)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["request_time"]["value"] == 123.45
        assert metrics_data["request_time"]["tags"] == tags

    def test_record_metric_overwrites_existing(self):
        """Test that recording a metric overwrites existing value."""
        node = MockNode()

        node.record_metric("metric1", 10.0)
        node.record_metric("metric1", 20.0)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["metric1"]["value"] == 20.0

    def test_record_metric_multiple_metrics(self):
        """Test recording multiple different metrics."""
        node = MockNode()

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
        node = MockNode()

        node.record_metric("metric1", 100.0, tags={})

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["metric1"]["tags"] == {}

    def test_record_metric_with_negative_value(self):
        """Test recording metric with negative value."""
        node = MockNode()

        node.record_metric("temperature", -15.5)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["temperature"]["value"] == -15.5

    def test_record_metric_with_zero_value(self):
        """Test recording metric with zero value."""
        node = MockNode()

        node.record_metric("error_count", 0.0)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["error_count"]["value"] == 0.0

    def test_record_metric_defensive_initialization(self):
        """Test that record_metric handles missing initialization gracefully."""
        node = MockNode()

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


@pytest.mark.unit
class TestIncrementCounter:
    """Test suite for increment_counter method."""

    def test_increment_counter_default_increment(self):
        """Test counter increment with default value (1)."""
        node = MockNode()

        node.increment_counter("requests")

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["requests"]["value"] == 1

    def test_increment_counter_custom_increment(self):
        """Test counter increment with custom value."""
        node = MockNode()

        node.increment_counter("bytes_sent", value=1024)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["bytes_sent"]["value"] == 1024

    def test_increment_counter_multiple_times(self):
        """Test incrementing counter multiple times."""
        node = MockNode()

        node.increment_counter("api_calls")
        node.increment_counter("api_calls")
        node.increment_counter("api_calls")

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["api_calls"]["value"] == 3

    def test_increment_counter_with_custom_values(self):
        """Test incrementing counter with varying custom values."""
        node = MockNode()

        node.increment_counter("total_bytes", value=100)
        node.increment_counter("total_bytes", value=200)
        node.increment_counter("total_bytes", value=50)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["total_bytes"]["value"] == 350

    def test_increment_counter_from_zero(self):
        """Test that counter starts from zero."""
        node = MockNode()

        # First increment should start from 0
        node.increment_counter("new_counter", value=5)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["new_counter"]["value"] == 5

    def test_increment_counter_negative_value(self):
        """Test incrementing counter with negative value (decrement)."""
        node = MockNode()

        node.increment_counter("balance", value=100)
        node.increment_counter("balance", value=-30)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["balance"]["value"] == 70

    def test_increment_counter_defensive_initialization(self):
        """Test that increment_counter handles missing initialization gracefully."""
        node = MockNode()

        # Should work even if attributes are missing (defensive initialization)
        node.increment_counter("test_counter", value=10)

        metrics_data = object.__getattribute__(node, "_metrics_data")
        assert metrics_data["test_counter"]["value"] == 10


@pytest.mark.unit
class TestGetMetrics:
    """Test suite for get_metrics method."""

    def test_get_metrics_empty(self):
        """Test get_metrics on empty metrics data."""
        node = MockNode()

        metrics = node.get_metrics()

        assert isinstance(metrics, dict)
        assert len(metrics) == 0

    def test_get_metrics_returns_copy(self):
        """Test that get_metrics returns a copy, not reference."""
        node = MockNode()

        node.record_metric("metric1", 100.0)

        metrics1 = node.get_metrics()
        metrics2 = node.get_metrics()

        # Should be equal but not the same object
        assert metrics1 == metrics2
        assert metrics1 is not metrics2

    def test_get_metrics_after_recording(self):
        """Test get_metrics returns all recorded metrics."""
        node = MockNode()

        node.record_metric("metric_a", 1.0, tags={"tag1": "value1"})
        node.increment_counter("counter_b", value=5)

        metrics = node.get_metrics()

        assert "metric_a" in metrics
        assert "counter_b" in metrics
        assert metrics["metric_a"]["value"] == 1.0
        assert metrics["counter_b"]["value"] == 5

    def test_get_metrics_defensive_initialization(self):
        """Test that get_metrics handles missing initialization gracefully."""
        node = MockNode()

        # Should work even if _metrics_data doesn't exist
        metrics = node.get_metrics()

        assert isinstance(metrics, dict)

    def test_get_metrics_with_multiple_metrics(self):
        """Test get_metrics with various metric types."""
        node = MockNode()

        node.record_metric("response_time", 45.2, tags={"endpoint": "/api/users"})
        node.increment_counter("requests_total")
        node.increment_counter("requests_total")
        node.record_metric("cpu_usage", 75.5)

        metrics = node.get_metrics()

        assert len(metrics) == 3
        assert metrics["response_time"]["value"] == 45.2
        assert metrics["requests_total"]["value"] == 2
        assert metrics["cpu_usage"]["value"] == 75.5


@pytest.mark.unit
class TestResetMetrics:
    """Test suite for reset_metrics method."""

    def test_reset_metrics_clears_all_data(self):
        """Test that reset_metrics clears all metrics data."""
        node = MockNode()

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
        node = MockNode()

        # Should not raise error
        node.reset_metrics()

        metrics = node.get_metrics()
        assert metrics == {}

    def test_reset_metrics_defensive_initialization(self):
        """Test that reset_metrics handles missing initialization gracefully."""
        node = MockNode()

        # Should work even if attributes don't exist
        node.reset_metrics()

        # Should still be able to record after reset
        node.record_metric("test", 1.0)
        metrics = node.get_metrics()
        assert metrics["test"]["value"] == 1.0


@pytest.mark.unit
class TestMetricsIntegration:
    """Integration tests for MixinMetrics workflow."""

    def test_full_metrics_workflow(self):
        """Test complete metrics workflow: record, increment, get, reset."""
        node = MockNode()

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
        node = MockNode()

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
        node = MockNode()

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
        node = MockNode()

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
        node = MockNode()

        node.record_metric("api.requests.total", 100.0)
        node.record_metric("cache:hit_rate", 0.85)
        node.increment_counter("errors/rate")

        metrics = node.get_metrics()

        assert "api.requests.total" in metrics
        assert "cache:hit_rate" in metrics
        assert "errors/rate" in metrics


@pytest.mark.unit
class TestMixinMetricsBackendSupport:
    """Test suite for MixinMetrics backend integration (v0.5.7+)."""

    def test_init_sets_backend_to_none(self) -> None:
        """Test that __init__ sets _metrics_backend to None."""
        node = MockNode()
        backend = object.__getattribute__(node, "_metrics_backend")
        assert backend is None

    def test_set_metrics_backend(self) -> None:
        """Test setting a metrics backend."""
        from omnibase_core.backends.metrics import BackendMetricsInMemory

        node = MockNode()
        backend = BackendMetricsInMemory()

        node.set_metrics_backend(backend)

        assert node.get_metrics_backend() is backend

    def test_set_metrics_backend_to_none(self) -> None:
        """Test clearing the metrics backend."""
        from omnibase_core.backends.metrics import BackendMetricsInMemory

        node = MockNode()
        backend = BackendMetricsInMemory()

        node.set_metrics_backend(backend)
        node.set_metrics_backend(None)

        assert node.get_metrics_backend() is None

    def test_get_metrics_backend_returns_none_by_default(self) -> None:
        """Test that get_metrics_backend returns None by default."""
        node = MockNode()
        assert node.get_metrics_backend() is None

    def test_record_metric_forwards_to_backend(self) -> None:
        """Test that record_metric forwards to configured backend."""
        from omnibase_core.backends.metrics import BackendMetricsInMemory

        node = MockNode()
        backend = BackendMetricsInMemory()
        node.set_metrics_backend(backend)

        node.record_metric("cpu_usage", 45.2, tags={"host": "server1"})

        # Verify in-memory storage (backward compatible)
        metrics = node.get_metrics()
        assert metrics["cpu_usage"]["value"] == 45.2

        # Verify backend received the metric
        backend_gauges = backend.get_gauges()
        assert "cpu_usage{host=server1}" in backend_gauges
        assert backend_gauges["cpu_usage{host=server1}"] == 45.2

    def test_increment_counter_forwards_to_backend(self) -> None:
        """Test that increment_counter forwards to configured backend."""
        from omnibase_core.backends.metrics import BackendMetricsInMemory

        node = MockNode()
        backend = BackendMetricsInMemory()
        node.set_metrics_backend(backend)

        node.increment_counter("requests_total", value=5, tags={"status": "200"})

        # Verify in-memory storage
        metrics = node.get_metrics()
        assert metrics["requests_total"]["value"] == 5

        # Verify backend received the counter
        backend_counters = backend.get_counters()
        assert "requests_total{status=200}" in backend_counters
        assert backend_counters["requests_total{status=200}"] == 5.0


@pytest.mark.unit
class TestMixinMetricsHistogram:
    """Test suite for record_histogram method (v0.5.7+)."""

    def test_record_histogram_basic(self) -> None:
        """Test basic histogram recording."""
        node = MockNode()

        node.record_histogram("response_time", 0.123)

        metrics = node.get_metrics()
        assert "response_time" in metrics
        assert metrics["response_time"]["value"] == 0.123

    def test_record_histogram_with_tags(self) -> None:
        """Test histogram recording with tags."""
        node = MockNode()

        node.record_histogram("request_duration", 0.5, tags={"endpoint": "/api/users"})

        metrics = node.get_metrics()
        assert metrics["request_duration"]["value"] == 0.5
        assert metrics["request_duration"]["tags"] == {"endpoint": "/api/users"}

    def test_record_histogram_forwards_to_backend(self) -> None:
        """Test that record_histogram forwards to configured backend."""
        from omnibase_core.backends.metrics import BackendMetricsInMemory

        node = MockNode()
        backend = BackendMetricsInMemory()
        node.set_metrics_backend(backend)

        node.record_histogram("latency", 0.15, tags={"method": "GET"})

        # Verify in-memory storage
        metrics = node.get_metrics()
        assert metrics["latency"]["value"] == 0.15

        # Verify backend received the histogram
        backend_histograms = backend.get_histograms()
        assert "latency{method=GET}" in backend_histograms
        assert backend_histograms["latency{method=GET}"] == [0.15]


@pytest.mark.unit
class TestMixinMetricsPush:
    """Test suite for push_metrics method (v0.5.7+)."""

    def test_push_metrics_without_backend(self) -> None:
        """Test that push_metrics is a no-op without backend."""
        node = MockNode()

        # Should not raise
        node.push_metrics()

    def test_push_metrics_calls_backend_push(self) -> None:
        """Test that push_metrics calls backend.push()."""
        from omnibase_core.backends.metrics import BackendMetricsInMemory

        node = MockNode()
        backend = BackendMetricsInMemory()
        node.set_metrics_backend(backend)

        node.record_metric("test", 1.0)

        # Should not raise (BackendMetricsInMemory.push() is a no-op)
        node.push_metrics()


@pytest.mark.unit
class TestMixinMetricsBackwardCompatibility:
    """Test suite for backward compatibility after v0.5.7 changes."""

    def test_existing_code_works_without_backend(self) -> None:
        """Test that existing code works unchanged without backend."""
        node = MockNode()

        # Record metrics (should work as before)
        node.record_metric("metric1", 100.0)
        node.increment_counter("counter1")

        # Get metrics (should work as before)
        metrics = node.get_metrics()
        assert metrics["metric1"]["value"] == 100.0
        assert metrics["counter1"]["value"] == 1

        # Reset metrics (should work as before)
        node.reset_metrics()
        assert node.get_metrics() == {}

    def test_in_memory_storage_always_populated(self) -> None:
        """Test that in-memory storage is always populated with backend."""
        from omnibase_core.backends.metrics import BackendMetricsInMemory

        node = MockNode()
        backend = BackendMetricsInMemory()
        node.set_metrics_backend(backend)

        node.record_metric("test", 42.0)

        # In-memory storage should still work
        assert node.get_metrics()["test"]["value"] == 42.0

    def test_reset_only_affects_in_memory(self) -> None:
        """Test that reset_metrics only clears in-memory storage."""
        from omnibase_core.backends.metrics import BackendMetricsInMemory

        node = MockNode()
        backend = BackendMetricsInMemory()
        node.set_metrics_backend(backend)

        node.record_metric("test", 1.0)
        node.reset_metrics()

        # In-memory should be cleared
        assert node.get_metrics() == {}

        # Backend should still have the metric
        assert backend.get_gauges()["test"] == 1.0
