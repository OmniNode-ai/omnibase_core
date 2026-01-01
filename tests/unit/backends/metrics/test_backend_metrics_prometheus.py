"""
Tests for BackendMetricsPrometheus - Prometheus metrics backend.

Coverage target: 85%+ (core functionality, mocking external dependencies)

Note:
    These tests require the prometheus-client package. They will be
    skipped automatically if the package is not installed.
"""

import pytest

# Skip entire module if prometheus-client is not available
pytest.importorskip("prometheus_client")

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
        """Test that same metric with different label sets fails with helpful error."""
        backend = BackendMetricsPrometheus()

        backend.record_gauge("http_requests", 100.0, tags={"method": "GET"})

        # Trying to record with different labels should fail with a helpful message
        with pytest.raises(
            ValueError, match="PROMETHEUS LABEL MISMATCH for gauge metric"
        ):
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


@pytest.mark.unit
class TestBackendMetricsPrometheusPushReturnValue:
    """Test suite for push() return value behavior."""

    def test_push_returns_false_without_gateway_url(self) -> None:
        """Test that push returns False when no gateway URL is configured."""
        backend = BackendMetricsPrometheus()

        result = backend.push()

        assert result is False

    def test_push_returns_false_without_job_name(self) -> None:
        """Test that push returns False when no job name is configured."""
        backend = BackendMetricsPrometheus(
            push_gateway_url="http://localhost:9091",
            push_job_name="",  # Empty job name
        )

        result = backend.push()

        assert result is False


@pytest.mark.unit
class TestBackendMetricsPrometheusLabelMismatchErrors:
    """Test suite for label mismatch error messages."""

    def test_gauge_label_mismatch_error_message_content(self) -> None:
        """Test that gauge label mismatch error contains helpful information."""
        backend = BackendMetricsPrometheus()
        backend.record_gauge("test_metric", 1.0, tags={"label_a": "value"})

        try:
            backend.record_gauge(
                "test_metric", 2.0, tags={"label_b": "value", "label_c": "value"}
            )
            pytest.fail("Should have raised ValueError")
        except ValueError as e:
            error_msg = str(e)
            # Check that the error message contains helpful information
            assert "PROMETHEUS LABEL MISMATCH" in error_msg
            assert "test_metric" in error_msg
            assert "First registration used labels:" in error_msg
            assert "Prometheus requires consistent label names" in error_msg
            assert "HOW TO FIX:" in error_msg

    def test_counter_label_mismatch_error_message_content(self) -> None:
        """Test that counter label mismatch error contains helpful information."""
        backend = BackendMetricsPrometheus()
        backend.increment_counter("test_counter", tags={"method": "GET"})

        try:
            backend.increment_counter("test_counter", tags={"status": "200"})
            pytest.fail("Should have raised ValueError")
        except ValueError as e:
            error_msg = str(e)
            assert "PROMETHEUS LABEL MISMATCH for counter metric" in error_msg
            assert "test_counter" in error_msg
            assert "'method'" in error_msg

    def test_histogram_label_mismatch_error_message_content(self) -> None:
        """Test that histogram label mismatch error contains helpful information."""
        backend = BackendMetricsPrometheus()
        backend.record_histogram("test_histogram", 0.5, tags={"endpoint": "/api"})

        try:
            backend.record_histogram("test_histogram", 0.8, tags={"region": "us"})
            pytest.fail("Should have raised ValueError")
        except ValueError as e:
            error_msg = str(e)
            assert "PROMETHEUS LABEL MISMATCH for histogram metric" in error_msg
            assert "test_histogram" in error_msg


@pytest.mark.unit
class TestBackendMetricsPrometheusCounterTagTracking:
    """Test suite for counter tag value combination tracking."""

    def test_counter_tag_combinations_tracked(self) -> None:
        """Test that counter tag value combinations are tracked."""
        backend = BackendMetricsPrometheus()

        backend.increment_counter("requests", tags={"method": "GET", "status": "200"})

        combinations = backend.get_counter_tag_combinations("requests")
        assert combinations is not None
        assert len(combinations) == 1
        assert frozenset([("method", "GET"), ("status", "200")]) in combinations

    def test_counter_multiple_tag_combinations_tracked(self) -> None:
        """Test that multiple tag value combinations are tracked."""
        backend = BackendMetricsPrometheus()

        backend.increment_counter("requests", tags={"method": "GET", "status": "200"})
        backend.increment_counter("requests", tags={"method": "POST", "status": "201"})
        backend.increment_counter("requests", tags={"method": "GET", "status": "404"})

        combinations = backend.get_counter_tag_combinations("requests")
        assert combinations is not None
        assert len(combinations) == 3

    def test_counter_same_combination_not_duplicated(self) -> None:
        """Test that same tag value combination is not duplicated."""
        backend = BackendMetricsPrometheus()

        backend.increment_counter("requests", tags={"method": "GET"})
        backend.increment_counter("requests", tags={"method": "GET"})
        backend.increment_counter("requests", tags={"method": "GET"})

        combinations = backend.get_counter_tag_combinations("requests")
        assert combinations is not None
        assert len(combinations) == 1

    def test_get_counter_tag_combinations_returns_none_for_unknown(self) -> None:
        """Test that get_counter_tag_combinations returns None for unknown counter."""
        backend = BackendMetricsPrometheus()

        combinations = backend.get_counter_tag_combinations("unknown_counter")

        assert combinations is None

    def test_counter_tag_combinations_with_prefix(self) -> None:
        """Test that tag combinations work correctly with prefixed counters."""
        backend = BackendMetricsPrometheus(prefix="myapp")

        backend.increment_counter("requests", tags={"method": "GET"})

        # Should be able to query by unprefixed name
        combinations = backend.get_counter_tag_combinations("requests")
        assert combinations is not None
        assert len(combinations) == 1

    def test_counter_without_tags_not_tracked(self) -> None:
        """Test that counters without tags don't create empty tracking."""
        backend = BackendMetricsPrometheus()

        backend.increment_counter("simple_counter")

        # Counter is created but no tag combinations should be tracked
        assert "simple_counter" in backend._counters
        # No entry in tag combinations for counters without tags
        assert "simple_counter" not in backend._counter_tag_combinations


@pytest.mark.unit
class TestBackendMetricsPrometheusEnhancedLabelErrors:
    """Test suite for enhanced label mismatch error messages."""

    def test_error_shows_missing_labels(self) -> None:
        """Test that error message shows which labels are missing."""
        backend = BackendMetricsPrometheus()
        backend.record_gauge("test", 1.0, tags={"a": "1", "b": "2"})

        try:
            backend.record_gauge("test", 2.0, tags={"a": "1"})
            pytest.fail("Should have raised ValueError")
        except ValueError as e:
            error_msg = str(e)
            assert "Missing labels (required but not provided):" in error_msg
            assert "'b'" in error_msg

    def test_error_shows_extra_labels(self) -> None:
        """Test that error message shows which labels are unexpected."""
        backend = BackendMetricsPrometheus()
        backend.record_gauge("test", 1.0, tags={"a": "1"})

        try:
            backend.record_gauge("test", 2.0, tags={"a": "1", "b": "2"})
            pytest.fail("Should have raised ValueError")
        except ValueError as e:
            error_msg = str(e)
            assert "Extra labels (provided but not expected):" in error_msg
            assert "'b'" in error_msg

    def test_error_shows_both_missing_and_extra(self) -> None:
        """Test that error shows both missing and extra labels."""
        backend = BackendMetricsPrometheus()
        backend.record_gauge("test", 1.0, tags={"a": "1", "b": "2"})

        try:
            backend.record_gauge("test", 2.0, tags={"a": "1", "c": "3"})
            pytest.fail("Should have raised ValueError")
        except ValueError as e:
            error_msg = str(e)
            assert "Missing labels (required but not provided):" in error_msg
            assert "'b'" in error_msg
            assert "Extra labels (provided but not expected):" in error_msg
            assert "'c'" in error_msg


@pytest.mark.unit
class TestBackendMetricsPrometheusGaugeTagTracking:
    """Test suite for gauge tag value combination tracking."""

    def test_gauge_tag_combinations_tracked(self) -> None:
        """Test that gauge tag value combinations are tracked."""
        backend = BackendMetricsPrometheus()

        backend.record_gauge("memory", 1024.0, tags={"host": "server1"})

        combinations = backend.get_gauge_tag_combinations("memory")
        assert combinations is not None
        assert len(combinations) == 1
        assert frozenset([("host", "server1")]) in combinations

    def test_gauge_multiple_tag_combinations(self) -> None:
        """Test that multiple gauge tag combinations are tracked."""
        backend = BackendMetricsPrometheus()

        backend.record_gauge("memory", 1024.0, tags={"host": "server1"})
        backend.record_gauge("memory", 2048.0, tags={"host": "server2"})

        combinations = backend.get_gauge_tag_combinations("memory")
        assert combinations is not None
        assert len(combinations) == 2


@pytest.mark.unit
class TestBackendMetricsPrometheusHistogramTagTracking:
    """Test suite for histogram tag value combination tracking."""

    def test_histogram_tag_combinations_tracked(self) -> None:
        """Test that histogram tag value combinations are tracked."""
        backend = BackendMetricsPrometheus()

        backend.record_histogram("latency", 0.5, tags={"endpoint": "/api"})

        combinations = backend.get_histogram_tag_combinations("latency")
        assert combinations is not None
        assert len(combinations) == 1
        assert frozenset([("endpoint", "/api")]) in combinations


@pytest.mark.unit
class TestBackendMetricsPrometheusCardinalityReport:
    """Test suite for cardinality report functionality."""

    def test_get_cardinality_report(self) -> None:
        """Test getting cardinality report for all metric types."""
        backend = BackendMetricsPrometheus()

        # Add metrics with various tag combinations
        backend.record_gauge("g1", 1.0, tags={"a": "1"})
        backend.record_gauge("g1", 2.0, tags={"a": "2"})
        backend.increment_counter("c1", tags={"b": "1"})
        backend.increment_counter("c1", tags={"b": "2"})
        backend.increment_counter("c1", tags={"b": "3"})
        backend.record_histogram("h1", 0.5, tags={"c": "1"})

        report = backend.get_cardinality_report()

        assert "gauge" in report
        assert "counter" in report
        assert "histogram" in report
        assert report["gauge"]["g1"] == 2
        assert report["counter"]["c1"] == 3
        assert report["histogram"]["h1"] == 1

    def test_get_all_tag_combinations(self) -> None:
        """Test getting all tag combinations."""
        backend = BackendMetricsPrometheus()

        backend.record_gauge("g1", 1.0, tags={"a": "1"})
        backend.increment_counter("c1", tags={"b": "1"})

        all_combos = backend.get_all_tag_combinations()

        assert "gauge" in all_combos
        assert "counter" in all_combos
        assert "histogram" in all_combos
        assert "g1" in all_combos["gauge"]
        assert "c1" in all_combos["counter"]


@pytest.mark.unit
class TestBackendMetricsPrometheusPushRetry:
    """Test suite for push gateway retry functionality."""

    def test_push_retry_configuration(self) -> None:
        """Test that push retry parameters can be configured."""
        backend = BackendMetricsPrometheus(
            push_retry_count=5,
            push_retry_delay=1.0,
            push_retry_backoff=3.0,
        )

        assert backend._push_retry_count == 5
        assert backend._push_retry_delay == 1.0
        assert backend._push_retry_backoff == 3.0

    def test_push_failure_stats_initial(self) -> None:
        """Test initial push failure stats are zero."""
        backend = BackendMetricsPrometheus()

        stats = backend.get_push_failure_stats()

        assert stats["consecutive_failures"] == 0
        assert stats["last_failure_time"] is None

    def test_cardinality_warning_threshold_configurable(self) -> None:
        """Test that cardinality warning threshold is configurable."""
        backend = BackendMetricsPrometheus(cardinality_warning_threshold=50)

        assert backend._cardinality_warning_threshold == 50


@pytest.mark.unit
class TestBackendMetricsPrometheusPushFailureError:
    """Test suite for push failure error formatting."""

    def test_format_push_failure_connection_error(self) -> None:
        """Test formatting of connection error with hints."""
        backend = BackendMetricsPrometheus(push_gateway_url="http://localhost:9091")

        class MockConnectionError(Exception):
            pass

        error = MockConnectionError("Connection refused")
        result = backend._format_push_failure_error(error)

        assert "MockConnectionError" in result
        assert "Connection refused" in result

    def test_format_push_failure_none_error(self) -> None:
        """Test formatting when error is None."""
        backend = BackendMetricsPrometheus()

        result = backend._format_push_failure_error(None)

        assert result == "Unknown error"

    def test_format_push_failure_timeout_hints(self) -> None:
        """Test that timeout errors get appropriate hints."""
        backend = BackendMetricsPrometheus(push_gateway_url="http://localhost:9091")

        class TimeoutError(Exception):
            pass

        error = TimeoutError("Request timed out")
        result = backend._format_push_failure_error(error)

        assert "timeout" in result.lower() or "Timeout" in result


@pytest.mark.unit
class TestBackendMetricsPrometheusDefaultValues:
    """Test suite for default value constants."""

    def test_default_retry_values(self) -> None:
        """Test that default retry values are sensible."""
        assert BackendMetricsPrometheus.DEFAULT_PUSH_RETRY_COUNT == 3
        assert BackendMetricsPrometheus.DEFAULT_PUSH_RETRY_DELAY == 0.5
        assert BackendMetricsPrometheus.DEFAULT_PUSH_RETRY_BACKOFF == 2.0
        assert BackendMetricsPrometheus.DEFAULT_CARDINALITY_WARNING_THRESHOLD == 100

    def test_default_values_used_when_none(self) -> None:
        """Test that defaults are used when None is passed."""
        backend = BackendMetricsPrometheus()

        assert backend._push_retry_count == 3
        assert backend._push_retry_delay == 0.5
        assert backend._push_retry_backoff == 2.0
        assert backend._cardinality_warning_threshold == 100
