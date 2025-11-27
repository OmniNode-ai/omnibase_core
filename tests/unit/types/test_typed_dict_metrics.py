"""
Test suite for TypedDictMetrics.
"""

from datetime import datetime

from omnibase_core.types.typed_dict_metrics import TypedDictMetrics


class TestTypedDictMetrics:
    """Test TypedDictMetrics functionality."""

    def test_typed_dict_metrics_creation(self):
        """Test creating TypedDictMetrics with all required fields."""
        metrics: TypedDictMetrics = {
            "timestamp": datetime.now(),
            "metric_name": "cpu_usage",
            "metric_value": 75.5,
            "metric_unit": "percent",
            "tags": {"host": "server1", "region": "us-east-1"},
        }

        assert metrics["metric_name"] == "cpu_usage"
        assert metrics["metric_value"] == 75.5
        assert metrics["metric_unit"] == "percent"
        assert metrics["tags"]["host"] == "server1"
        assert isinstance(metrics["timestamp"], datetime)

    def test_typed_dict_metrics_different_metric_types(self):
        """Test TypedDictMetrics with different metric types."""
        test_cases = [
            {
                "metric_name": "memory_usage",
                "metric_value": 1024.0,
                "metric_unit": "MB",
                "tags": {"type": "heap"},
            },
            {
                "metric_name": "response_time",
                "metric_value": 0.5,
                "metric_unit": "seconds",
                "tags": {"endpoint": "/api/users"},
            },
            {
                "metric_name": "error_rate",
                "metric_value": 0.02,
                "metric_unit": "ratio",
                "tags": {"service": "auth"},
            },
        ]

        for test_case in test_cases:
            metrics: TypedDictMetrics = {
                "timestamp": datetime.now(),
                **test_case,
            }

            assert metrics["metric_name"] == test_case["metric_name"]
            assert metrics["metric_value"] == test_case["metric_value"]
            assert metrics["metric_unit"] == test_case["metric_unit"]
            assert metrics["tags"] == test_case["tags"]

    def test_typed_dict_metrics_field_types(self):
        """Test that all fields have correct types."""
        metrics: TypedDictMetrics = {
            "timestamp": datetime(2024, 1, 1, 12, 0, 0),
            "metric_name": "test_metric",
            "metric_value": 42.0,
            "metric_unit": "count",
            "tags": {"key": "value"},
        }

        assert isinstance(metrics["timestamp"], datetime)
        assert isinstance(metrics["metric_name"], str)
        assert isinstance(metrics["metric_value"], float)
        assert isinstance(metrics["metric_unit"], str)
        assert isinstance(metrics["tags"], dict)

    def test_typed_dict_metrics_empty_tags(self):
        """Test TypedDictMetrics with empty tags."""
        metrics: TypedDictMetrics = {
            "timestamp": datetime.now(),
            "metric_name": "simple_metric",
            "metric_value": 100.0,
            "metric_unit": "units",
            "tags": {},
        }

        assert metrics["tags"] == {}
        assert len(metrics["tags"]) == 0

    def test_typed_dict_metrics_multiple_tags(self):
        """Test TypedDictMetrics with multiple tags."""
        metrics: TypedDictMetrics = {
            "timestamp": datetime.now(),
            "metric_name": "complex_metric",
            "metric_value": 200.0,
            "metric_unit": "requests",
            "tags": {
                "service": "api",
                "version": "v1.2.3",
                "environment": "production",
                "datacenter": "us-west-2",
            },
        }

        assert len(metrics["tags"]) == 4
        assert metrics["tags"]["service"] == "api"
        assert metrics["tags"]["version"] == "v1.2.3"
        assert metrics["tags"]["environment"] == "production"
        assert metrics["tags"]["datacenter"] == "us-west-2"

    def test_typed_dict_metrics_zero_value(self):
        """Test TypedDictMetrics with zero value."""
        metrics: TypedDictMetrics = {
            "timestamp": datetime.now(),
            "metric_name": "zero_metric",
            "metric_value": 0.0,
            "metric_unit": "count",
            "tags": {"type": "counter"},
        }

        assert metrics["metric_value"] == 0.0

    def test_typed_dict_metrics_negative_value(self):
        """Test TypedDictMetrics with negative value."""
        metrics: TypedDictMetrics = {
            "timestamp": datetime.now(),
            "metric_name": "temperature",
            "metric_value": -10.5,
            "metric_unit": "celsius",
            "tags": {"sensor": "outdoor"},
        }

        assert metrics["metric_value"] == -10.5

    def test_typed_dict_metrics_high_precision_value(self):
        """Test TypedDictMetrics with high precision value."""
        metrics: TypedDictMetrics = {
            "timestamp": datetime.now(),
            "metric_name": "precision_metric",
            "metric_value": 3.14159265359,
            "metric_unit": "ratio",
            "tags": {"calculation": "pi"},
        }

        assert metrics["metric_value"] == 3.14159265359

    def test_typed_dict_metrics_timestamp_formats(self):
        """Test TypedDictMetrics with different timestamp formats."""
        now = datetime.now()
        iso_timestamp = datetime.fromisoformat("2024-01-01T12:00:00")

        metrics1: TypedDictMetrics = {
            "timestamp": now,
            "metric_name": "current_metric",
            "metric_value": 1.0,
            "metric_unit": "count",
            "tags": {"time": "now"},
        }

        metrics2: TypedDictMetrics = {
            "timestamp": iso_timestamp,
            "metric_name": "historical_metric",
            "metric_value": 2.0,
            "metric_unit": "count",
            "tags": {"time": "historical"},
        }

        assert metrics1["timestamp"] == now
        assert metrics2["timestamp"] == iso_timestamp
