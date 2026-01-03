# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelCapabilityMetrics handler.

TDD tests - written FIRST before implementation.
These tests define the expected behavior for the ModelCapabilityMetrics handler,
which provides performance metrics collection as a standalone handler (no mixin inheritance).

Ticket: OMN-1112 - Convert MixinMetrics to handler pattern.

Coverage target: 60%+ (stub implementation with defensive attribute handling)
"""

import pytest

from omnibase_core.pipeline.handlers.model_capability_metrics import (
    ModelCapabilityMetrics,
)


@pytest.mark.unit
class TestModelCapabilityMetricsInit:
    """Test suite for ModelCapabilityMetrics initialization."""

    def test_init_with_default_values(self) -> None:
        """Test initialization with default values."""
        handler = ModelCapabilityMetrics()

        assert handler.namespace == "onex"
        assert handler.enabled is True

    def test_init_with_custom_namespace(self) -> None:
        """Test initialization with custom namespace."""
        handler = ModelCapabilityMetrics(namespace="custom_app")

        assert handler.namespace == "custom_app"
        assert handler.enabled is True

    def test_init_with_disabled_metrics(self) -> None:
        """Test initialization with metrics disabled."""
        handler = ModelCapabilityMetrics(enabled=False)

        assert handler.enabled is False

    def test_init_with_all_custom_values(self) -> None:
        """Test initialization with all custom values."""
        handler = ModelCapabilityMetrics(
            namespace="my_service",
            enabled=True,
        )

        assert handler.namespace == "my_service"
        assert handler.enabled is True

    def test_init_creates_empty_metrics_data(self) -> None:
        """Test that initialization creates empty metrics data."""
        handler = ModelCapabilityMetrics()

        metrics = handler.get_metrics()
        assert metrics == {}
        assert isinstance(metrics, dict)


@pytest.mark.unit
class TestRecordMetric:
    """Test suite for record_metric method."""

    def test_record_metric_basic(self) -> None:
        """Test basic metric recording."""
        handler = ModelCapabilityMetrics()

        handler.record_metric("test_metric", 42.5)

        metrics = handler.get_metrics()
        assert "test_metric" in metrics
        assert metrics["test_metric"]["value"] == 42.5
        assert metrics["test_metric"]["tags"] == {}

    def test_record_metric_with_tags(self) -> None:
        """Test metric recording with tags."""
        handler = ModelCapabilityMetrics()
        tags = {"env": "test", "service": "api"}

        handler.record_metric("request_time", 123.45, tags=tags)

        metrics = handler.get_metrics()
        assert metrics["request_time"]["value"] == 123.45
        assert metrics["request_time"]["tags"] == tags

    def test_record_metric_overwrites_existing(self) -> None:
        """Test that recording a metric overwrites existing value."""
        handler = ModelCapabilityMetrics()

        handler.record_metric("metric1", 10.0)
        handler.record_metric("metric1", 20.0)

        metrics = handler.get_metrics()
        assert metrics["metric1"]["value"] == 20.0

    def test_record_metric_multiple_metrics(self) -> None:
        """Test recording multiple different metrics."""
        handler = ModelCapabilityMetrics()

        handler.record_metric("metric_a", 1.0)
        handler.record_metric("metric_b", 2.0)
        handler.record_metric("metric_c", 3.0)

        metrics = handler.get_metrics()
        assert len(metrics) == 3
        assert metrics["metric_a"]["value"] == 1.0
        assert metrics["metric_b"]["value"] == 2.0
        assert metrics["metric_c"]["value"] == 3.0

    def test_record_metric_with_empty_tags(self) -> None:
        """Test recording metric with explicitly empty tags."""
        handler = ModelCapabilityMetrics()

        handler.record_metric("metric1", 100.0, tags={})

        metrics = handler.get_metrics()
        assert metrics["metric1"]["tags"] == {}

    def test_record_metric_with_negative_value(self) -> None:
        """Test recording metric with negative value."""
        handler = ModelCapabilityMetrics()

        handler.record_metric("temperature", -15.5)

        metrics = handler.get_metrics()
        assert metrics["temperature"]["value"] == -15.5

    def test_record_metric_with_zero_value(self) -> None:
        """Test recording metric with zero value."""
        handler = ModelCapabilityMetrics()

        handler.record_metric("error_count", 0.0)

        metrics = handler.get_metrics()
        assert metrics["error_count"]["value"] == 0.0

    def test_record_metric_when_disabled(self) -> None:
        """Test that record_metric does nothing when disabled."""
        handler = ModelCapabilityMetrics(enabled=False)

        handler.record_metric("test_metric", 42.5)

        metrics = handler.get_metrics()
        assert len(metrics) == 0


@pytest.mark.unit
class TestIncrementCounter:
    """Test suite for increment_counter method."""

    def test_increment_counter_default_increment(self) -> None:
        """Test counter increment with default value (1)."""
        handler = ModelCapabilityMetrics()

        handler.increment_counter("requests")

        metrics = handler.get_metrics()
        assert metrics["requests"]["value"] == 1

    def test_increment_counter_custom_increment(self) -> None:
        """Test counter increment with custom value."""
        handler = ModelCapabilityMetrics()

        handler.increment_counter("bytes_sent", value=1024)

        metrics = handler.get_metrics()
        assert metrics["bytes_sent"]["value"] == 1024

    def test_increment_counter_multiple_times(self) -> None:
        """Test incrementing counter multiple times."""
        handler = ModelCapabilityMetrics()

        handler.increment_counter("api_calls")
        handler.increment_counter("api_calls")
        handler.increment_counter("api_calls")

        metrics = handler.get_metrics()
        assert metrics["api_calls"]["value"] == 3

    def test_increment_counter_with_custom_values(self) -> None:
        """Test incrementing counter with varying custom values."""
        handler = ModelCapabilityMetrics()

        handler.increment_counter("total_bytes", value=100)
        handler.increment_counter("total_bytes", value=200)
        handler.increment_counter("total_bytes", value=50)

        metrics = handler.get_metrics()
        assert metrics["total_bytes"]["value"] == 350

    def test_increment_counter_from_zero(self) -> None:
        """Test that counter starts from zero."""
        handler = ModelCapabilityMetrics()

        # First increment should start from 0
        handler.increment_counter("new_counter", value=5)

        metrics = handler.get_metrics()
        assert metrics["new_counter"]["value"] == 5

    def test_increment_counter_negative_value(self) -> None:
        """Test incrementing counter with negative value (decrement)."""
        handler = ModelCapabilityMetrics()

        handler.increment_counter("balance", value=100)
        handler.increment_counter("balance", value=-30)

        metrics = handler.get_metrics()
        assert metrics["balance"]["value"] == 70

    def test_increment_counter_when_disabled(self) -> None:
        """Test that increment_counter does nothing when disabled."""
        handler = ModelCapabilityMetrics(enabled=False)

        handler.increment_counter("test_counter", value=10)

        metrics = handler.get_metrics()
        assert len(metrics) == 0


@pytest.mark.unit
class TestGetMetrics:
    """Test suite for get_metrics method."""

    def test_get_metrics_empty(self) -> None:
        """Test get_metrics on empty metrics data."""
        handler = ModelCapabilityMetrics()

        metrics = handler.get_metrics()

        assert isinstance(metrics, dict)
        assert len(metrics) == 0

    def test_get_metrics_returns_copy(self) -> None:
        """Test that get_metrics returns a copy, not reference."""
        handler = ModelCapabilityMetrics()

        handler.record_metric("metric1", 100.0)

        metrics1 = handler.get_metrics()
        metrics2 = handler.get_metrics()

        # Should be equal but not the same object
        assert metrics1 == metrics2
        assert metrics1 is not metrics2

    def test_get_metrics_modification_does_not_affect_internal(self) -> None:
        """Test that modifying returned dict does not affect internal state."""
        handler = ModelCapabilityMetrics()

        handler.record_metric("metric1", 100.0)

        metrics = handler.get_metrics()
        metrics["metric1"] = {"value": 999.0, "tags": {}}  # Modify returned copy

        # Internal state should be unchanged
        fresh_metrics = handler.get_metrics()
        assert fresh_metrics["metric1"]["value"] == 100.0

    def test_get_metrics_after_recording(self) -> None:
        """Test get_metrics returns all recorded metrics."""
        handler = ModelCapabilityMetrics()

        handler.record_metric("metric_a", 1.0, tags={"tag1": "value1"})
        handler.increment_counter("counter_b", value=5)

        metrics = handler.get_metrics()

        assert "metric_a" in metrics
        assert "counter_b" in metrics
        assert metrics["metric_a"]["value"] == 1.0
        assert metrics["counter_b"]["value"] == 5

    def test_get_metrics_with_multiple_metrics(self) -> None:
        """Test get_metrics with various metric types."""
        handler = ModelCapabilityMetrics()

        handler.record_metric("response_time", 45.2, tags={"endpoint": "/api/users"})
        handler.increment_counter("requests_total")
        handler.increment_counter("requests_total")
        handler.record_metric("cpu_usage", 75.5)

        metrics = handler.get_metrics()

        assert len(metrics) == 3
        assert metrics["response_time"]["value"] == 45.2
        assert metrics["requests_total"]["value"] == 2
        assert metrics["cpu_usage"]["value"] == 75.5


@pytest.mark.unit
class TestResetMetrics:
    """Test suite for reset_metrics method."""

    def test_reset_metrics_clears_all_data(self) -> None:
        """Test that reset_metrics clears all metrics data."""
        handler = ModelCapabilityMetrics()

        # Record some metrics
        handler.record_metric("metric1", 10.0)
        handler.increment_counter("counter1")
        handler.record_metric("metric2", 20.0)

        # Verify metrics exist
        metrics_before = handler.get_metrics()
        assert len(metrics_before) == 3

        # Reset
        handler.reset_metrics()

        # Verify metrics are cleared
        metrics_after = handler.get_metrics()
        assert len(metrics_after) == 0
        assert metrics_after == {}

    def test_reset_metrics_on_empty(self) -> None:
        """Test reset_metrics on already empty metrics."""
        handler = ModelCapabilityMetrics()

        # Should not raise error
        handler.reset_metrics()

        metrics = handler.get_metrics()
        assert metrics == {}

    def test_reset_metrics_allows_new_recording(self) -> None:
        """Test that new metrics can be recorded after reset."""
        handler = ModelCapabilityMetrics()

        # Record and reset
        handler.record_metric("old_metric", 100.0)
        handler.reset_metrics()

        # Should still be able to record after reset
        handler.record_metric("new_metric", 1.0)
        metrics = handler.get_metrics()

        assert "old_metric" not in metrics
        assert metrics["new_metric"]["value"] == 1.0


@pytest.mark.unit
class TestMetricsIsolation:
    """Test suite for metrics isolation between instances."""

    def test_metrics_isolated_per_instance(self) -> None:
        """Test that metrics are isolated between handler instances."""
        handler1 = ModelCapabilityMetrics()
        handler2 = ModelCapabilityMetrics()

        handler1.record_metric("metric1", 100.0)
        handler2.record_metric("metric2", 200.0)

        metrics1 = handler1.get_metrics()
        metrics2 = handler2.get_metrics()

        # Each instance should only have its own metrics
        assert "metric1" in metrics1
        assert "metric2" not in metrics1
        assert "metric2" in metrics2
        assert "metric1" not in metrics2

    def test_counters_isolated_per_instance(self) -> None:
        """Test that counters are isolated between handler instances."""
        handler1 = ModelCapabilityMetrics()
        handler2 = ModelCapabilityMetrics()

        handler1.increment_counter("counter", value=10)
        handler2.increment_counter("counter", value=5)

        metrics1 = handler1.get_metrics()
        metrics2 = handler2.get_metrics()

        assert metrics1["counter"]["value"] == 10
        assert metrics2["counter"]["value"] == 5

    def test_reset_does_not_affect_other_instances(self) -> None:
        """Test that resetting one handler doesn't affect others."""
        handler1 = ModelCapabilityMetrics()
        handler2 = ModelCapabilityMetrics()

        handler1.record_metric("metric", 100.0)
        handler2.record_metric("metric", 200.0)

        handler1.reset_metrics()

        metrics1 = handler1.get_metrics()
        metrics2 = handler2.get_metrics()

        assert len(metrics1) == 0
        assert metrics2["metric"]["value"] == 200.0


@pytest.mark.unit
class TestStandaloneHandler:
    """Test suite to verify handler works standalone without mixin inheritance."""

    def test_handler_works_without_inheritance(self) -> None:
        """Test that handler works as standalone class (no mixin required)."""
        # Create handler directly - no need for mock node or inheritance
        handler = ModelCapabilityMetrics()

        # Should work without any base class
        handler.record_metric("standalone_metric", 42.0)
        handler.increment_counter("standalone_counter")

        metrics = handler.get_metrics()
        assert metrics["standalone_metric"]["value"] == 42.0
        assert metrics["standalone_counter"]["value"] == 1

    def test_handler_can_be_composed(self) -> None:
        """Test that handler can be composed with other objects."""
        handler = ModelCapabilityMetrics()

        # Simulate composition pattern
        class MyPipelineStep:
            def __init__(self, metrics_handler: ModelCapabilityMetrics) -> None:
                self.metrics = metrics_handler

            def execute(self) -> None:
                self.metrics.increment_counter("executions")
                self.metrics.record_metric("execution_time_ms", 123.45)

        step = MyPipelineStep(handler)
        step.execute()

        metrics = handler.get_metrics()
        assert metrics["executions"]["value"] == 1
        assert metrics["execution_time_ms"]["value"] == 123.45

    def test_handler_multiple_namespaces(self) -> None:
        """Test handlers with different namespaces for different components."""
        api_metrics = ModelCapabilityMetrics(namespace="api")
        db_metrics = ModelCapabilityMetrics(namespace="database")

        api_metrics.increment_counter("requests")
        db_metrics.increment_counter("queries")

        assert api_metrics.namespace == "api"
        assert db_metrics.namespace == "database"

        # Metrics should be independent
        api = api_metrics.get_metrics()
        db = db_metrics.get_metrics()

        assert "requests" in api
        assert "queries" not in api
        assert "queries" in db
        assert "requests" not in db


@pytest.mark.unit
class TestMetricsIntegration:
    """Integration tests for ModelCapabilityMetrics workflow."""

    def test_full_metrics_workflow(self) -> None:
        """Test complete metrics workflow: record, increment, get, reset."""
        handler = ModelCapabilityMetrics()

        # Record various metrics
        handler.record_metric("latency_ms", 250.5, tags={"service": "api"})
        handler.increment_counter("api_calls")
        handler.increment_counter("api_calls")
        handler.increment_counter("api_calls")
        handler.record_metric("memory_mb", 512.0)

        # Get metrics
        metrics = handler.get_metrics()
        assert len(metrics) == 3
        assert metrics["latency_ms"]["value"] == 250.5
        assert metrics["api_calls"]["value"] == 3
        assert metrics["memory_mb"]["value"] == 512.0

        # Reset
        handler.reset_metrics()
        metrics_after = handler.get_metrics()
        assert len(metrics_after) == 0

        # Can record new metrics after reset
        handler.record_metric("new_metric", 1.0)
        metrics_new = handler.get_metrics()
        assert len(metrics_new) == 1

    def test_counter_and_metric_coexistence(self) -> None:
        """Test that counters and regular metrics work together."""
        handler = ModelCapabilityMetrics()

        # Mix of counters and regular metrics
        handler.increment_counter("request_count", value=10)
        handler.record_metric("avg_response_time", 123.45)
        handler.increment_counter("error_count", value=2)
        handler.record_metric("success_rate", 0.95)

        metrics = handler.get_metrics()

        assert len(metrics) == 4
        assert metrics["request_count"]["value"] == 10
        assert metrics["avg_response_time"]["value"] == 123.45
        assert metrics["error_count"]["value"] == 2
        assert metrics["success_rate"]["value"] == 0.95

    def test_metric_overwrite_behavior(self) -> None:
        """Test how metrics behave when overwritten."""
        handler = ModelCapabilityMetrics()

        # Record initial value
        handler.record_metric("temperature", 20.0, tags={"unit": "celsius"})

        initial_metrics = handler.get_metrics()
        assert initial_metrics["temperature"]["value"] == 20.0
        assert initial_metrics["temperature"]["tags"] == {"unit": "celsius"}

        # Overwrite with new value and tags
        handler.record_metric(
            "temperature", 25.0, tags={"unit": "celsius", "location": "room1"}
        )

        updated_metrics = handler.get_metrics()
        assert updated_metrics["temperature"]["value"] == 25.0
        assert updated_metrics["temperature"]["tags"] == {
            "unit": "celsius",
            "location": "room1",
        }

    def test_large_number_of_metrics(self) -> None:
        """Test handling of many metrics."""
        handler = ModelCapabilityMetrics()

        # Record many metrics
        for i in range(100):
            handler.record_metric(f"metric_{i}", float(i))

        metrics = handler.get_metrics()
        assert len(metrics) == 100

        # Verify some values
        assert metrics["metric_0"]["value"] == 0.0
        assert metrics["metric_50"]["value"] == 50.0
        assert metrics["metric_99"]["value"] == 99.0

    def test_metrics_with_special_characters_in_names(self) -> None:
        """Test metrics with special characters in names."""
        handler = ModelCapabilityMetrics()

        handler.record_metric("api.requests.total", 100.0)
        handler.record_metric("cache:hit_rate", 0.85)
        handler.increment_counter("errors/rate")

        metrics = handler.get_metrics()

        assert "api.requests.total" in metrics
        assert "cache:hit_rate" in metrics
        assert "errors/rate" in metrics

    def test_metrics_with_unicode_tag_values(self) -> None:
        """Test metrics with unicode characters in tag values."""
        handler = ModelCapabilityMetrics()

        handler.record_metric(
            "request_time",
            100.0,
            tags={"region": "eu-west", "user": "test_user"},
        )

        metrics = handler.get_metrics()
        assert metrics["request_time"]["tags"]["region"] == "eu-west"
        assert metrics["request_time"]["tags"]["user"] == "test_user"
