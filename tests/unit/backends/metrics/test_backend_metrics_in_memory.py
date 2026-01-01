"""
Tests for BackendMetricsInMemory - In-memory metrics backend.

Coverage target: 90%+ (core functionality)
"""

import pytest

from omnibase_core.backends.metrics import BackendMetricsInMemory
from omnibase_core.protocols.metrics import ProtocolMetricsBackend


@pytest.mark.unit
class TestBackendMetricsInMemoryInit:
    """Test suite for BackendMetricsInMemory initialization."""

    def test_init_creates_empty_storage(self) -> None:
        """Test that initialization creates empty storage."""
        backend = BackendMetricsInMemory()

        assert backend.get_gauges() == {}
        assert backend.get_counters() == {}
        assert backend.get_histograms() == {}

    def test_implements_protocol(self) -> None:
        """Test that BackendMetricsInMemory implements ProtocolMetricsBackend."""
        backend = BackendMetricsInMemory()

        # Protocol conformance check
        assert isinstance(backend, ProtocolMetricsBackend)


@pytest.mark.unit
class TestBackendMetricsInMemoryGauges:
    """Test suite for gauge metric recording."""

    def test_record_gauge_basic(self) -> None:
        """Test basic gauge recording."""
        backend = BackendMetricsInMemory()

        backend.record_gauge("memory_usage", 1024.0)

        gauges = backend.get_gauges()
        assert "memory_usage" in gauges
        assert gauges["memory_usage"] == 1024.0

    def test_record_gauge_with_tags(self) -> None:
        """Test gauge recording with tags."""
        backend = BackendMetricsInMemory()

        backend.record_gauge("cpu_usage", 45.2, tags={"host": "server1"})

        gauges = backend.get_gauges()
        assert "cpu_usage{host=server1}" in gauges
        assert gauges["cpu_usage{host=server1}"] == 45.2

    def test_record_gauge_with_multiple_tags(self) -> None:
        """Test gauge recording with multiple tags."""
        backend = BackendMetricsInMemory()

        backend.record_gauge(
            "request_duration",
            0.5,
            tags={"method": "GET", "endpoint": "/api/users"},
        )

        gauges = backend.get_gauges()
        # Tags should be sorted alphabetically
        assert "request_duration{endpoint=/api/users,method=GET}" in gauges
        assert gauges["request_duration{endpoint=/api/users,method=GET}"] == 0.5

    def test_record_gauge_overwrites_existing(self) -> None:
        """Test that recording a gauge overwrites existing value."""
        backend = BackendMetricsInMemory()

        backend.record_gauge("temperature", 20.0)
        backend.record_gauge("temperature", 25.0)

        gauges = backend.get_gauges()
        assert gauges["temperature"] == 25.0

    def test_record_gauge_negative_value(self) -> None:
        """Test recording gauge with negative value."""
        backend = BackendMetricsInMemory()

        backend.record_gauge("temperature", -15.5)

        gauges = backend.get_gauges()
        assert gauges["temperature"] == -15.5


@pytest.mark.unit
class TestBackendMetricsInMemoryCounters:
    """Test suite for counter metric recording."""

    def test_increment_counter_default(self) -> None:
        """Test counter increment with default value."""
        backend = BackendMetricsInMemory()

        backend.increment_counter("requests_total")

        counters = backend.get_counters()
        assert "requests_total" in counters
        assert counters["requests_total"] == 1.0

    def test_increment_counter_custom_value(self) -> None:
        """Test counter increment with custom value."""
        backend = BackendMetricsInMemory()

        backend.increment_counter("bytes_sent", value=1024.0)

        counters = backend.get_counters()
        assert counters["bytes_sent"] == 1024.0

    def test_increment_counter_with_tags(self) -> None:
        """Test counter increment with tags."""
        backend = BackendMetricsInMemory()

        backend.increment_counter("requests_total", tags={"status": "200"})

        counters = backend.get_counters()
        assert "requests_total{status=200}" in counters
        assert counters["requests_total{status=200}"] == 1.0

    def test_increment_counter_accumulates(self) -> None:
        """Test that counter increments accumulate."""
        backend = BackendMetricsInMemory()

        backend.increment_counter("api_calls")
        backend.increment_counter("api_calls")
        backend.increment_counter("api_calls", value=3.0)

        counters = backend.get_counters()
        assert counters["api_calls"] == 5.0


@pytest.mark.unit
class TestBackendMetricsInMemoryHistograms:
    """Test suite for histogram metric recording."""

    def test_record_histogram_basic(self) -> None:
        """Test basic histogram recording."""
        backend = BackendMetricsInMemory()

        backend.record_histogram("response_time", 0.123)

        histograms = backend.get_histograms()
        assert "response_time" in histograms
        assert histograms["response_time"] == [0.123]

    def test_record_histogram_with_tags(self) -> None:
        """Test histogram recording with tags."""
        backend = BackendMetricsInMemory()

        backend.record_histogram(
            "request_duration", 0.5, tags={"endpoint": "/api/users"}
        )

        histograms = backend.get_histograms()
        assert "request_duration{endpoint=/api/users}" in histograms
        assert histograms["request_duration{endpoint=/api/users}"] == [0.5]

    def test_record_histogram_accumulates(self) -> None:
        """Test that histogram observations accumulate."""
        backend = BackendMetricsInMemory()

        backend.record_histogram("latency", 0.1)
        backend.record_histogram("latency", 0.2)
        backend.record_histogram("latency", 0.3)

        histograms = backend.get_histograms()
        assert histograms["latency"] == [0.1, 0.2, 0.3]


@pytest.mark.unit
class TestBackendMetricsInMemoryUtilities:
    """Test suite for utility methods."""

    def test_push_is_noop(self) -> None:
        """Test that push is a no-op for in-memory backend."""
        backend = BackendMetricsInMemory()

        backend.record_gauge("test", 1.0)

        # Should not raise
        backend.push()

        # Data should still be there
        assert backend.get_gauges()["test"] == 1.0

    def test_clear_removes_all_metrics(self) -> None:
        """Test that clear removes all collected metrics."""
        backend = BackendMetricsInMemory()

        backend.record_gauge("gauge1", 1.0)
        backend.increment_counter("counter1")
        backend.record_histogram("histogram1", 0.5)

        backend.clear()

        assert backend.get_gauges() == {}
        assert backend.get_counters() == {}
        assert backend.get_histograms() == {}

    def test_get_returns_copies(self) -> None:
        """Test that get methods return copies."""
        backend = BackendMetricsInMemory()

        backend.record_gauge("test", 1.0)
        backend.increment_counter("counter", 5.0)
        backend.record_histogram("hist", 0.5)

        gauges = backend.get_gauges()
        counters = backend.get_counters()
        histograms = backend.get_histograms()

        # Modify the returned copies
        gauges["test"] = 999.0
        counters["counter"] = 999.0
        histograms["hist"].append(999.0)

        # Original data should be unchanged
        assert backend.get_gauges()["test"] == 1.0
        assert backend.get_counters()["counter"] == 5.0
        assert backend.get_histograms()["hist"] == [0.5]


@pytest.mark.unit
class TestBackendMetricsInMemoryKeyGeneration:
    """Test suite for metric key generation."""

    def test_key_without_tags(self) -> None:
        """Test key generation without tags."""
        backend = BackendMetricsInMemory()

        backend.record_gauge("simple_metric", 1.0)

        gauges = backend.get_gauges()
        assert "simple_metric" in gauges

    def test_key_with_empty_tags(self) -> None:
        """Test key generation with empty tags dict."""
        backend = BackendMetricsInMemory()

        backend.record_gauge("metric", 1.0, tags={})

        gauges = backend.get_gauges()
        assert "metric" in gauges

    def test_key_with_single_tag(self) -> None:
        """Test key generation with single tag."""
        backend = BackendMetricsInMemory()

        backend.record_gauge("metric", 1.0, tags={"key": "value"})

        gauges = backend.get_gauges()
        assert "metric{key=value}" in gauges

    def test_key_tags_sorted_alphabetically(self) -> None:
        """Test that tags are sorted alphabetically in key."""
        backend = BackendMetricsInMemory()

        backend.record_gauge("metric", 1.0, tags={"z": "1", "a": "2", "m": "3"})

        gauges = backend.get_gauges()
        assert "metric{a=2,m=3,z=1}" in gauges

    def test_different_tags_create_different_metrics(self) -> None:
        """Test that different tag combinations create different metrics."""
        backend = BackendMetricsInMemory()

        backend.record_gauge("http_requests", 100.0, tags={"status": "200"})
        backend.record_gauge("http_requests", 10.0, tags={"status": "500"})
        backend.record_gauge("http_requests", 50.0)  # No tags

        gauges = backend.get_gauges()
        assert len(gauges) == 3
        assert gauges["http_requests{status=200}"] == 100.0
        assert gauges["http_requests{status=500}"] == 10.0
        assert gauges["http_requests"] == 50.0
