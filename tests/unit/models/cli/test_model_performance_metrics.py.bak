"""
Unit tests for ModelPerformanceMetrics.

Tests performance metrics model with protocol implementations and validation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.cli.model_cli_performance_metrics import (
    ModelPerformanceMetrics,
)


class TestModelPerformanceMetricsBasics:
    """Test basic initialization and validation."""

    def test_minimal_initialization(self):
        """Test model with only required field."""
        metrics = ModelPerformanceMetrics(execution_time_ms=100.5)

        assert metrics.execution_time_ms == 100.5
        assert metrics.memory_usage_mb == 0.0
        assert metrics.cpu_usage_percent == 0.0
        assert metrics.io_operations == 0
        assert metrics.network_calls == 0

    def test_full_initialization(self):
        """Test model with all fields specified."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=250.75,
            memory_usage_mb=128.5,
            cpu_usage_percent=45.2,
            io_operations=10,
            network_calls=5,
        )

        assert metrics.execution_time_ms == 250.75
        assert metrics.memory_usage_mb == 128.5
        assert metrics.cpu_usage_percent == 45.2
        assert metrics.io_operations == 10
        assert metrics.network_calls == 5

    def test_missing_required_field(self):
        """Test that execution_time_ms is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPerformanceMetrics()  # type: ignore[call-arg]

        assert "execution_time_ms" in str(exc_info.value)

    def test_zero_execution_time(self):
        """Test with zero execution time."""
        metrics = ModelPerformanceMetrics(execution_time_ms=0.0)

        assert metrics.execution_time_ms == 0.0

    def test_negative_execution_time(self):
        """Test with negative execution time (should be allowed)."""
        metrics = ModelPerformanceMetrics(execution_time_ms=-1.0)

        assert metrics.execution_time_ms == -1.0


class TestModelPerformanceMetricsProtocols:
    """Test protocol method implementations."""

    def test_serialize_minimal(self):
        """Test serialization with minimal data."""
        metrics = ModelPerformanceMetrics(execution_time_ms=100.0)
        data = metrics.serialize()

        assert isinstance(data, dict)
        assert data["execution_time_ms"] == 100.0
        assert data["memory_usage_mb"] == 0.0
        assert data["cpu_usage_percent"] == 0.0
        assert data["io_operations"] == 0
        assert data["network_calls"] == 0

    def test_serialize_full(self):
        """Test serialization with all fields."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=150.5,
            memory_usage_mb=64.2,
            cpu_usage_percent=25.7,
            io_operations=8,
            network_calls=3,
        )
        data = metrics.serialize()

        assert data["execution_time_ms"] == 150.5
        assert data["memory_usage_mb"] == 64.2
        assert data["cpu_usage_percent"] == 25.7
        assert data["io_operations"] == 8
        assert data["network_calls"] == 3

    def test_serialize_preserves_types(self):
        """Test that serialization preserves data types."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=100.0,
            io_operations=5,
        )
        data = metrics.serialize()

        assert isinstance(data["execution_time_ms"], float)
        assert isinstance(data["memory_usage_mb"], float)
        assert isinstance(data["cpu_usage_percent"], float)
        assert isinstance(data["io_operations"], int)
        assert isinstance(data["network_calls"], int)

    def test_get_name_default(self):
        """Test default name generation."""
        metrics = ModelPerformanceMetrics(execution_time_ms=100.0)
        name = metrics.get_name()

        assert "ModelPerformanceMetrics" in name
        assert "Unnamed" in name

    def test_get_name_no_name_field(self):
        """Test get_name when model has no name field."""
        metrics = ModelPerformanceMetrics(execution_time_ms=100.0)

        # Should fall back to class name
        name = metrics.get_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_set_name_no_field(self):
        """Test set_name when no name field exists."""
        metrics = ModelPerformanceMetrics(execution_time_ms=100.0)

        # Should not raise, but also won't set anything
        metrics.set_name("test_metrics")

        # Name still returns default
        assert "Unnamed" in metrics.get_name()

    def test_validate_instance_success(self):
        """Test successful instance validation."""
        metrics = ModelPerformanceMetrics(execution_time_ms=100.0)

        result = metrics.validate_instance()

        assert result is True

    def test_validate_instance_with_all_fields(self):
        """Test validation with all fields populated."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=200.0,
            memory_usage_mb=256.0,
            cpu_usage_percent=75.5,
            io_operations=20,
            network_calls=10,
        )

        result = metrics.validate_instance()

        assert result is True


class TestModelPerformanceMetricsEdgeCases:
    """Test edge cases and boundary values."""

    def test_large_execution_time(self):
        """Test with very large execution time."""
        metrics = ModelPerformanceMetrics(execution_time_ms=999999999.99)

        assert metrics.execution_time_ms == 999999999.99

    def test_large_memory_usage(self):
        """Test with very large memory usage."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=100.0,
            memory_usage_mb=999999.99,
        )

        assert metrics.memory_usage_mb == 999999.99

    def test_cpu_usage_over_100(self):
        """Test CPU usage over 100% (should be allowed)."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=100.0,
            cpu_usage_percent=250.0,  # Multi-core can exceed 100%
        )

        assert metrics.cpu_usage_percent == 250.0

    def test_large_io_operations(self):
        """Test with large number of IO operations."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=100.0,
            io_operations=1000000,
        )

        assert metrics.io_operations == 1000000

    def test_large_network_calls(self):
        """Test with large number of network calls."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=100.0,
            network_calls=50000,
        )

        assert metrics.network_calls == 50000

    def test_fractional_values(self):
        """Test with various fractional values."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=0.001,
            memory_usage_mb=0.5,
            cpu_usage_percent=0.1,
        )

        assert metrics.execution_time_ms == 0.001
        assert metrics.memory_usage_mb == 0.5
        assert metrics.cpu_usage_percent == 0.1


class TestModelPerformanceMetricsConfig:
    """Test model configuration."""

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=100.0,
            unknown_field="value",  # type: ignore[call-arg]
        )

        assert metrics.execution_time_ms == 100.0
        assert not hasattr(metrics, "unknown_field")

    def test_validate_assignment(self):
        """Test validate_assignment config."""
        metrics = ModelPerformanceMetrics(execution_time_ms=100.0)

        # Should allow valid assignment
        metrics.execution_time_ms = 200.0
        assert metrics.execution_time_ms == 200.0

        metrics.memory_usage_mb = 128.0
        assert metrics.memory_usage_mb == 128.0

    def test_model_dump(self):
        """Test Pydantic model_dump method."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=100.0,
            memory_usage_mb=64.0,
        )

        data = metrics.model_dump()

        assert isinstance(data, dict)
        assert "execution_time_ms" in data
        assert "memory_usage_mb" in data

    def test_model_dump_exclude_none(self):
        """Test model_dump with exclude_none."""
        metrics = ModelPerformanceMetrics(execution_time_ms=100.0)

        # Default values are 0, not None, so should be included
        data = metrics.model_dump(exclude_none=True)

        assert "execution_time_ms" in data
        assert "memory_usage_mb" in data  # 0.0 is not None


class TestModelPerformanceMetricsComparisons:
    """Test metric comparisons and calculations."""

    def test_create_multiple_instances(self):
        """Test creating multiple independent instances."""
        metrics1 = ModelPerformanceMetrics(execution_time_ms=100.0)
        metrics2 = ModelPerformanceMetrics(execution_time_ms=200.0)

        assert metrics1.execution_time_ms == 100.0
        assert metrics2.execution_time_ms == 200.0
        assert metrics1 != metrics2

    def test_metrics_equality(self):
        """Test metrics equality."""
        metrics1 = ModelPerformanceMetrics(
            execution_time_ms=100.0,
            memory_usage_mb=64.0,
            cpu_usage_percent=50.0,
            io_operations=10,
            network_calls=5,
        )
        metrics2 = ModelPerformanceMetrics(
            execution_time_ms=100.0,
            memory_usage_mb=64.0,
            cpu_usage_percent=50.0,
            io_operations=10,
            network_calls=5,
        )

        assert metrics1 == metrics2

    def test_metrics_inequality(self):
        """Test metrics inequality."""
        metrics1 = ModelPerformanceMetrics(execution_time_ms=100.0)
        metrics2 = ModelPerformanceMetrics(execution_time_ms=200.0)

        assert metrics1 != metrics2

    def test_update_metrics(self):
        """Test updating metrics after creation."""
        metrics = ModelPerformanceMetrics(execution_time_ms=100.0)

        # Update values
        metrics.memory_usage_mb = 128.0
        metrics.cpu_usage_percent = 45.5
        metrics.io_operations = 15
        metrics.network_calls = 8

        assert metrics.memory_usage_mb == 128.0
        assert metrics.cpu_usage_percent == 45.5
        assert metrics.io_operations == 15
        assert metrics.network_calls == 8


class TestModelPerformanceMetricsRealisticScenarios:
    """Test realistic usage scenarios."""

    def test_fast_execution_low_resources(self):
        """Test metrics for fast, low-resource execution."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=10.5,
            memory_usage_mb=2.3,
            cpu_usage_percent=5.0,
            io_operations=1,
            network_calls=0,
        )

        assert metrics.execution_time_ms < 20
        assert metrics.memory_usage_mb < 10
        assert metrics.cpu_usage_percent < 10

    def test_slow_execution_high_resources(self):
        """Test metrics for slow, high-resource execution."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=5000.0,
            memory_usage_mb=512.0,
            cpu_usage_percent=95.0,
            io_operations=100,
            network_calls=50,
        )

        assert metrics.execution_time_ms > 1000
        assert metrics.memory_usage_mb > 100
        assert metrics.cpu_usage_percent > 50

    def test_io_intensive_operation(self):
        """Test metrics for I/O intensive operation."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=2000.0,
            memory_usage_mb=128.0,
            cpu_usage_percent=25.0,
            io_operations=500,
            network_calls=0,
        )

        assert metrics.io_operations > 100
        assert metrics.network_calls == 0

    def test_network_intensive_operation(self):
        """Test metrics for network intensive operation."""
        metrics = ModelPerformanceMetrics(
            execution_time_ms=3000.0,
            memory_usage_mb=64.0,
            cpu_usage_percent=15.0,
            io_operations=10,
            network_calls=100,
        )

        assert metrics.network_calls > 50
        assert metrics.io_operations < 50
