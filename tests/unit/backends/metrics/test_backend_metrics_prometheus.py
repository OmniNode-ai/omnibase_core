"""
Tests for BackendMetricsPrometheus - Prometheus metrics backend.

Coverage target: 85%+ (core functionality, mocking external dependencies)
"""

import pytest

from omnibase_core.backends.metrics import BackendMetricsPrometheus
from omnibase_core.protocols.metrics import ProtocolMetricsBackend


@pytest.mark.unit
class TestBackendMetricsPrometheusInit:
    """Test suite for BackendMetricsPrometheus initialization."""

    def test_init_creates_empty_storage(self) -> None:
        """Test that initialization creates empty metric storage."""
        backend = BackendMetricsPrometheus()

        # Should not have any metrics registered yet
        assert backend._gauges == {}
        assert backend._counters == {}
        assert backend._histograms == {}

    def test_init_with_prefix(self) -> None:
        """Test initialization with prefix."""
        backend = BackendMetricsPrometheus(prefix="myapp")

        assert backend._prefix == "myapp"

    def test_init_with_push_gateway(self) -> None:
        """Test initialization with push gateway configuration."""
        backend = BackendMetricsPrometheus(
            push_gateway_url="http://localhost:9091",
            push_job_name="test_job",
        )

        assert backend._push_gateway_url == "http://localhost:9091"
        assert backend._push_job_name == "test_job"

    def test_implements_protocol(self) -> None:
        """Test that BackendMetricsPrometheus implements ProtocolMetricsBackend."""
        backend = BackendMetricsPrometheus()

        # Protocol conformance check
        assert isinstance(backend, ProtocolMetricsBackend)


@pytest.mark.unit
class TestBackendMetricsPrometheusGauges:
    """Test suite for Prometheus gauge metric recording."""

    def test_record_gauge_basic(self) -> None:
        """Test basic gauge recording."""
        backend = BackendMetricsPrometheus()

        backend.record_gauge("memory_usage", 1024.0)

        # Gauge should be registered
        assert "memory_usage" in backend._gauges

    def test_record_gauge_with_prefix(self) -> None:
        """Test gauge recording with prefix."""
        backend = BackendMetricsPrometheus(prefix="myapp")

        backend.record_gauge("memory_usage", 1024.0)

        # Gauge should have prefixed name
        assert "myapp_memory_usage" in backend._gauges

    def test_record_gauge_with_tags(self) -> None:
        """Test gauge recording with tags (labels)."""
        backend = BackendMetricsPrometheus()

        backend.record_gauge("cpu_usage", 45.2, tags={"host": "server1"})

        # Gauge should be registered with labels
        assert "cpu_usage" in backend._gauges
        assert "cpu_usage" in backend._gauge_labels
        assert backend._gauge_labels["cpu_usage"] == ("host",)

    def test_record_gauge_multiple_values(self) -> None:
        """Test recording multiple gauge values (overwrites)."""
        backend = BackendMetricsPrometheus()

        backend.record_gauge("temperature", 20.0)
        backend.record_gauge("temperature", 25.0)
        backend.record_gauge("temperature", 30.0)

        # Should still only have one gauge registered
        assert len(backend._gauges) == 1

    def test_record_gauge_same_metric_different_labels_fails(self) -> None:
        """Test that same metric with different label sets fails."""
        backend = BackendMetricsPrometheus()

        backend.record_gauge("http_requests", 100.0, tags={"method": "GET"})

        # Trying to record with different labels should fail
        with pytest.raises(ValueError, match="already exists with different labels"):
            backend.record_gauge(
                "http_requests", 50.0, tags={"method": "GET", "status": "200"}
            )


@pytest.mark.unit
class TestBackendMetricsPrometheusCounters:
    """Test suite for Prometheus counter metric recording."""

    def test_increment_counter_basic(self) -> None:
        """Test basic counter increment."""
        backend = BackendMetricsPrometheus()

        backend.increment_counter("requests_total")

        assert "requests_total" in backend._counters

    def test_increment_counter_with_prefix(self) -> None:
        """Test counter increment with prefix."""
        backend = BackendMetricsPrometheus(prefix="myapp")

        backend.increment_counter("requests_total")

        assert "myapp_requests_total" in backend._counters

    def test_increment_counter_with_tags(self) -> None:
        """Test counter increment with tags."""
        backend = BackendMetricsPrometheus()

        backend.increment_counter("requests_total", tags={"status": "200"})

        assert "requests_total" in backend._counters
        assert backend._counter_labels["requests_total"] == ("status",)

    def test_increment_counter_custom_value(self) -> None:
        """Test counter increment with custom value."""
        backend = BackendMetricsPrometheus()

        backend.increment_counter("bytes_sent", value=1024.0)

        assert "bytes_sent" in backend._counters


@pytest.mark.unit
class TestBackendMetricsPrometheusHistograms:
    """Test suite for Prometheus histogram metric recording."""

    def test_record_histogram_basic(self) -> None:
        """Test basic histogram recording."""
        backend = BackendMetricsPrometheus()

        backend.record_histogram("response_time", 0.123)

        assert "response_time" in backend._histograms

    def test_record_histogram_with_prefix(self) -> None:
        """Test histogram recording with prefix."""
        backend = BackendMetricsPrometheus(prefix="myapp")

        backend.record_histogram("response_time", 0.123)

        assert "myapp_response_time" in backend._histograms

    def test_record_histogram_with_tags(self) -> None:
        """Test histogram recording with tags."""
        backend = BackendMetricsPrometheus()

        backend.record_histogram(
            "request_duration", 0.5, tags={"endpoint": "/api/users"}
        )

        assert "request_duration" in backend._histograms
        assert backend._histogram_labels["request_duration"] == ("endpoint",)

    def test_record_histogram_with_custom_buckets(self) -> None:
        """Test histogram with custom bucket configuration."""
        backend = BackendMetricsPrometheus(
            default_histogram_buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
        )

        backend.record_histogram("latency", 0.25)

        assert "latency" in backend._histograms


@pytest.mark.unit
class TestBackendMetricsPrometheusPush:
    """Test suite for push functionality."""

    def test_push_without_gateway_is_noop(self) -> None:
        """Test that push without gateway URL is a no-op."""
        backend = BackendMetricsPrometheus()

        # Should not raise
        backend.push()


@pytest.mark.unit
class TestBackendMetricsPrometheusRegistry:
    """Test suite for registry access."""

    def test_get_registry_returns_registry(self) -> None:
        """Test that get_registry returns the collector registry."""
        from prometheus_client import CollectorRegistry

        backend = BackendMetricsPrometheus()

        registry = backend.get_registry()

        assert isinstance(registry, CollectorRegistry)

    def test_custom_registry(self) -> None:
        """Test using a custom registry."""
        from prometheus_client import CollectorRegistry

        custom_registry = CollectorRegistry()
        backend = BackendMetricsPrometheus(registry=custom_registry)

        assert backend.get_registry() is custom_registry


@pytest.mark.unit
class TestBackendMetricsPrometheusNameGeneration:
    """Test suite for metric name generation."""

    def test_make_name_without_prefix(self) -> None:
        """Test name generation without prefix."""
        backend = BackendMetricsPrometheus()

        result = backend._make_name("test_metric")

        assert result == "test_metric"

    def test_make_name_with_prefix(self) -> None:
        """Test name generation with prefix."""
        backend = BackendMetricsPrometheus(prefix="myapp")

        result = backend._make_name("test_metric")

        assert result == "myapp_test_metric"

    def test_make_name_with_trailing_underscore_prefix(self) -> None:
        """Test name generation with trailing underscore in prefix."""
        backend = BackendMetricsPrometheus(prefix="myapp_")

        result = backend._make_name("test_metric")

        assert result == "myapp_test_metric"


@pytest.mark.unit
class TestBackendMetricsPrometheusIntegration:
    """Integration tests for complete workflows."""

    def test_full_metrics_workflow(self) -> None:
        """Test complete workflow with all metric types."""
        backend = BackendMetricsPrometheus(prefix="test")

        # Record various metrics
        backend.record_gauge("memory_mb", 512.0)
        backend.increment_counter("requests_total")
        backend.record_histogram("latency_seconds", 0.15)

        # All metrics should be registered
        assert "test_memory_mb" in backend._gauges
        assert "test_requests_total" in backend._counters
        assert "test_latency_seconds" in backend._histograms

    def test_metrics_with_consistent_labels(self) -> None:
        """Test recording metrics with consistent label sets."""
        backend = BackendMetricsPrometheus()

        # Multiple values with same label set should work
        backend.record_gauge("http_requests", 100.0, tags={"method": "GET"})
        backend.record_gauge("http_requests", 200.0, tags={"method": "POST"})

        # Should only have one gauge registered
        assert len(backend._gauges) == 1
        assert backend._gauge_labels["http_requests"] == ("method",)

    def test_multiple_tag_ordering(self) -> None:
        """Test that tags are consistently ordered."""
        backend = BackendMetricsPrometheus()

        # Tags should be sorted, so order of input shouldn't matter
        backend.record_gauge("metric1", 1.0, tags={"b": "2", "a": "1"})

        assert backend._gauge_labels["metric1"] == ("a", "b")
