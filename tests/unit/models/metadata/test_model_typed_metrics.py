"""Tests for ModelTypedMetrics."""

from uuid import uuid4

from omnibase_core.models.metadata.model_typed_metrics import ModelTypedMetrics


class TestModelTypedMetricsInstantiation:
    """Tests for ModelTypedMetrics instantiation."""

    def test_create_with_required_fields_string(self):
        """Test creating typed metrics with required string fields."""
        metric_id = uuid4()
        metric = ModelTypedMetrics[str](
            metric_id=metric_id,
            metric_display_name="Test Metric",
            value="test_value",
        )
        assert metric.metric_id == metric_id
        assert metric.metric_display_name == "Test Metric"
        assert metric.value == "test_value"
        assert metric.unit == ""
        assert metric.description == ""

    def test_create_with_required_fields_int(self):
        """Test creating typed metrics with required integer fields."""
        metric_id = uuid4()
        metric = ModelTypedMetrics[int](
            metric_id=metric_id,
            metric_display_name="Count Metric",
            value=42,
        )
        assert metric.metric_id == metric_id
        assert metric.value == 42

    def test_create_with_required_fields_float(self):
        """Test creating typed metrics with required float fields."""
        metric_id = uuid4()
        metric = ModelTypedMetrics[float](
            metric_id=metric_id,
            metric_display_name="Performance Metric",
            value=3.14159,
        )
        assert metric.metric_id == metric_id
        assert metric.value == 3.14159

    def test_create_with_required_fields_bool(self):
        """Test creating typed metrics with required boolean fields."""
        metric_id = uuid4()
        metric = ModelTypedMetrics[bool](
            metric_id=metric_id,
            metric_display_name="Status Metric",
            value=True,
        )
        assert metric.metric_id == metric_id
        assert metric.value is True

    def test_create_with_all_fields(self):
        """Test creating typed metrics with all fields."""
        metric_id = uuid4()
        metric = ModelTypedMetrics[str](
            metric_id=metric_id,
            metric_display_name="Complete Metric",
            value="test_value",
            unit="requests/sec",
            description="A complete test metric",
        )
        assert metric.metric_id == metric_id
        assert metric.metric_display_name == "Complete Metric"
        assert metric.value == "test_value"
        assert metric.unit == "requests/sec"
        assert metric.description == "A complete test metric"


class TestModelTypedMetricsStringMetric:
    """Tests for string_metric factory method."""

    def test_string_metric_basic(self):
        """Test creating string metric with basic fields."""
        metric = ModelTypedMetrics.string_metric(
            name="test_metric",
            value="test_value",
        )
        assert isinstance(metric, ModelTypedMetrics)
        assert metric.metric_display_name == "test_metric"
        assert metric.value == "test_value"
        assert metric.unit == ""
        assert metric.description == ""

    def test_string_metric_with_unit(self):
        """Test creating string metric with unit."""
        metric = ModelTypedMetrics.string_metric(
            name="status",
            value="active",
            unit="state",
        )
        assert metric.metric_display_name == "status"
        assert metric.value == "active"
        assert metric.unit == "state"

    def test_string_metric_with_description(self):
        """Test creating string metric with description."""
        metric = ModelTypedMetrics.string_metric(
            name="endpoint",
            value="/api/v1/users",
            description="User API endpoint",
        )
        assert metric.metric_display_name == "endpoint"
        assert metric.value == "/api/v1/users"
        assert metric.description == "User API endpoint"

    def test_string_metric_with_all_fields(self):
        """Test creating string metric with all fields."""
        metric = ModelTypedMetrics.string_metric(
            name="environment",
            value="production",
            unit="env",
            description="Deployment environment",
        )
        assert metric.metric_display_name == "environment"
        assert metric.value == "production"
        assert metric.unit == "env"
        assert metric.description == "Deployment environment"

    def test_string_metric_id_deterministic(self):
        """Test that string metric generates deterministic UUID from name."""
        metric1 = ModelTypedMetrics.string_metric(name="test", value="value1")
        metric2 = ModelTypedMetrics.string_metric(name="test", value="value2")
        # Same name should generate same metric_id
        assert metric1.metric_id == metric2.metric_id

    def test_string_metric_id_different_names(self):
        """Test that different names generate different UUIDs."""
        metric1 = ModelTypedMetrics.string_metric(name="test1", value="value")
        metric2 = ModelTypedMetrics.string_metric(name="test2", value="value")
        # Different names should generate different metric_ids
        assert metric1.metric_id != metric2.metric_id


class TestModelTypedMetricsIntMetric:
    """Tests for int_metric factory method."""

    def test_int_metric_basic(self):
        """Test creating int metric with basic fields."""
        metric = ModelTypedMetrics.int_metric(
            name="request_count",
            value=100,
        )
        assert isinstance(metric, ModelTypedMetrics)
        assert metric.metric_display_name == "request_count"
        assert metric.value == 100
        assert isinstance(metric.value, int)

    def test_int_metric_with_unit(self):
        """Test creating int metric with unit."""
        metric = ModelTypedMetrics.int_metric(
            name="memory_usage",
            value=1024,
            unit="MB",
        )
        assert metric.value == 1024
        assert metric.unit == "MB"

    def test_int_metric_with_description(self):
        """Test creating int metric with description."""
        metric = ModelTypedMetrics.int_metric(
            name="error_count",
            value=5,
            description="Number of errors encountered",
        )
        assert metric.value == 5
        assert metric.description == "Number of errors encountered"

    def test_int_metric_zero_value(self):
        """Test int metric with zero value."""
        metric = ModelTypedMetrics.int_metric(name="zero_test", value=0)
        assert metric.value == 0

    def test_int_metric_negative_value(self):
        """Test int metric with negative value."""
        metric = ModelTypedMetrics.int_metric(name="delta", value=-50)
        assert metric.value == -50

    def test_int_metric_large_value(self):
        """Test int metric with large value."""
        large_value = 999_999_999
        metric = ModelTypedMetrics.int_metric(name="large", value=large_value)
        assert metric.value == large_value


class TestModelTypedMetricsFloatMetric:
    """Tests for float_metric factory method."""

    def test_float_metric_basic(self):
        """Test creating float metric with basic fields."""
        metric = ModelTypedMetrics.float_metric(
            name="response_time",
            value=1.234,
        )
        assert isinstance(metric, ModelTypedMetrics)
        assert metric.metric_display_name == "response_time"
        assert metric.value == 1.234
        assert isinstance(metric.value, float)

    def test_float_metric_with_unit(self):
        """Test creating float metric with unit."""
        metric = ModelTypedMetrics.float_metric(
            name="cpu_usage",
            value=75.5,
            unit="%",
        )
        assert metric.value == 75.5
        assert metric.unit == "%"

    def test_float_metric_with_description(self):
        """Test creating float metric with description."""
        metric = ModelTypedMetrics.float_metric(
            name="latency",
            value=0.045,
            description="Average latency in seconds",
        )
        assert metric.value == 0.045
        assert metric.description == "Average latency in seconds"

    def test_float_metric_zero_value(self):
        """Test float metric with zero value."""
        metric = ModelTypedMetrics.float_metric(name="zero", value=0.0)
        assert metric.value == 0.0

    def test_float_metric_negative_value(self):
        """Test float metric with negative value."""
        metric = ModelTypedMetrics.float_metric(name="temperature", value=-5.5)
        assert metric.value == -5.5

    def test_float_metric_precision(self):
        """Test float metric with high precision."""
        precise_value = 3.141592653589793
        metric = ModelTypedMetrics.float_metric(name="pi", value=precise_value)
        assert metric.value == precise_value


class TestModelTypedMetricsBooleanMetric:
    """Tests for boolean_metric factory method."""

    def test_boolean_metric_true(self):
        """Test creating boolean metric with True value."""
        metric = ModelTypedMetrics.boolean_metric(
            name="is_active",
            value=True,
        )
        assert isinstance(metric, ModelTypedMetrics)
        assert metric.metric_display_name == "is_active"
        assert metric.value is True
        assert isinstance(metric.value, bool)

    def test_boolean_metric_false(self):
        """Test creating boolean metric with False value."""
        metric = ModelTypedMetrics.boolean_metric(
            name="is_disabled",
            value=False,
        )
        assert metric.value is False

    def test_boolean_metric_with_unit(self):
        """Test creating boolean metric with unit."""
        metric = ModelTypedMetrics.boolean_metric(
            name="enabled",
            value=True,
            unit="flag",
        )
        assert metric.value is True
        assert metric.unit == "flag"

    def test_boolean_metric_with_description(self):
        """Test creating boolean metric with description."""
        metric = ModelTypedMetrics.boolean_metric(
            name="feature_enabled",
            value=False,
            description="Feature flag status",
        )
        assert metric.value is False
        assert metric.description == "Feature flag status"


class TestModelTypedMetricsProtocols:
    """Tests for ModelTypedMetrics protocol implementations."""

    def test_get_metadata(self):
        """Test get_metadata method."""
        metric = ModelTypedMetrics.string_metric(
            name="test",
            value="value",
            description="Test metric",
        )
        metadata = metric.get_metadata()
        assert isinstance(metadata, dict)
        assert "description" in metadata

    def test_set_metadata(self):
        """Test set_metadata method."""
        metric = ModelTypedMetrics.string_metric(name="test", value="value")
        result = metric.set_metadata({"description": "New description"})
        assert result is True
        assert metric.description == "New description"

    def test_set_metadata_nonexistent_field(self):
        """Test set_metadata with nonexistent field."""
        metric = ModelTypedMetrics.string_metric(name="test", value="value")
        result = metric.set_metadata({"nonexistent": "value"})
        assert result is True  # Should return True but not set the field

    def test_serialize(self):
        """Test serialize method."""
        metric = ModelTypedMetrics.string_metric(
            name="test",
            value="value",
            unit="unit",
        )
        data = metric.serialize()
        assert isinstance(data, dict)
        assert "metric_id" in data
        assert "metric_display_name" in data
        assert "value" in data
        assert "unit" in data

    def test_validate_instance(self):
        """Test validate_instance method."""
        metric = ModelTypedMetrics.string_metric(name="test", value="value")
        assert metric.validate_instance() is True


class TestModelTypedMetricsSerialization:
    """Tests for ModelTypedMetrics serialization."""

    def test_model_dump_string_metric(self):
        """Test model_dump for string metric."""
        metric = ModelTypedMetrics.string_metric(
            name="test",
            value="test_value",
            unit="unit",
            description="description",
        )
        data = metric.model_dump()
        assert data["metric_display_name"] == "test"
        assert data["value"] == "test_value"
        assert data["unit"] == "unit"
        assert data["description"] == "description"

    def test_model_dump_int_metric(self):
        """Test model_dump for int metric."""
        metric = ModelTypedMetrics.int_metric(name="count", value=42)
        data = metric.model_dump()
        assert data["value"] == 42
        assert isinstance(data["value"], int)

    def test_model_dump_float_metric(self):
        """Test model_dump for float metric."""
        metric = ModelTypedMetrics.float_metric(name="ratio", value=0.75)
        data = metric.model_dump()
        assert data["value"] == 0.75
        assert isinstance(data["value"], float)

    def test_model_dump_bool_metric(self):
        """Test model_dump for boolean metric."""
        metric = ModelTypedMetrics.boolean_metric(name="flag", value=True)
        data = metric.model_dump()
        assert data["value"] is True
        assert isinstance(data["value"], bool)


class TestModelTypedMetricsEdgeCases:
    """Tests for ModelTypedMetrics edge cases."""

    def test_empty_metric_display_name(self):
        """Test metric with empty display name."""
        metric_id = uuid4()
        metric = ModelTypedMetrics[str](
            metric_id=metric_id,
            metric_display_name="",
            value="test",
        )
        assert metric.metric_display_name == ""

    def test_very_long_metric_display_name(self):
        """Test metric with very long display name."""
        long_name = "metric_" * 100
        metric = ModelTypedMetrics.string_metric(name=long_name, value="test")
        assert metric.metric_display_name == long_name

    def test_special_characters_in_value(self):
        """Test string metric with special characters."""
        special_value = "!@#$%^&*()[]{}|\\;:'\",<.>/?"
        metric = ModelTypedMetrics.string_metric(name="special", value=special_value)
        assert metric.value == special_value

    def test_unicode_in_value(self):
        """Test string metric with unicode characters."""
        unicode_value = "Hello 世界 🌍"
        metric = ModelTypedMetrics.string_metric(name="unicode", value=unicode_value)
        assert metric.value == unicode_value

    def test_empty_string_value(self):
        """Test string metric with empty value."""
        metric = ModelTypedMetrics.string_metric(name="empty", value="")
        assert metric.value == ""

    def test_very_large_int_value(self):
        """Test int metric with very large value."""
        large_int = 2**63 - 1  # Max 64-bit signed integer
        metric = ModelTypedMetrics.int_metric(name="large", value=large_int)
        assert metric.value == large_int

    def test_very_small_float_value(self):
        """Test float metric with very small value."""
        small_float = 1e-308
        metric = ModelTypedMetrics.float_metric(name="small", value=small_float)
        assert metric.value == small_float

    def test_inf_float_value(self):
        """Test float metric with infinity."""
        metric = ModelTypedMetrics.float_metric(name="inf", value=float("inf"))
        assert metric.value == float("inf")

    def test_metric_id_consistency(self):
        """Test that metric_id is consistent for same name across types."""
        str_metric = ModelTypedMetrics.string_metric(name="test", value="val")
        int_metric = ModelTypedMetrics.int_metric(name="test", value=1)
        float_metric = ModelTypedMetrics.float_metric(name="test", value=1.0)
        bool_metric = ModelTypedMetrics.boolean_metric(name="test", value=True)

        # All should have the same metric_id since they use the same name
        assert str_metric.metric_id == int_metric.metric_id
        assert int_metric.metric_id == float_metric.metric_id
        assert float_metric.metric_id == bool_metric.metric_id
