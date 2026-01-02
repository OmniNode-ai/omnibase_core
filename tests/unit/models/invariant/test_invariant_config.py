"""Tests for invariant configuration models."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.invariant import (
    ModelCostConfig,
    ModelCustomInvariantConfig,
    ModelFieldPresenceConfig,
    ModelFieldValueConfig,
    ModelLatencyConfig,
    ModelSchemaInvariantConfig,
    ModelThresholdConfig,
)


@pytest.mark.unit
class TestLatencyConfig:
    """Test ModelLatencyConfig."""

    def test_latency_requires_max_ms(self) -> None:
        """Latency type must specify max_ms."""
        with pytest.raises(ValidationError):
            ModelLatencyConfig()

    def test_latency_max_ms_must_be_positive(self) -> None:
        """max_ms must be > 0."""
        with pytest.raises(ValidationError):
            ModelLatencyConfig(max_ms=0)

    def test_latency_max_ms_cannot_be_negative(self) -> None:
        """max_ms cannot be negative."""
        with pytest.raises(ValidationError):
            ModelLatencyConfig(max_ms=-100)

    def test_latency_valid_config(self) -> None:
        """Valid latency config."""
        config = ModelLatencyConfig(max_ms=5000)
        assert config.max_ms == 5000

    def test_latency_config_with_large_value(self) -> None:
        """Latency config accepts large values."""
        config = ModelLatencyConfig(max_ms=300000)  # 5 minutes
        assert config.max_ms == 300000

    def test_latency_config_with_small_value(self) -> None:
        """Latency config accepts small positive values."""
        config = ModelLatencyConfig(max_ms=1)
        assert config.max_ms == 1

    def test_latency_config_serialization(self) -> None:
        """Latency config serializes correctly."""
        config = ModelLatencyConfig(max_ms=5000)
        data = config.model_dump()
        assert data["max_ms"] == 5000


@pytest.mark.unit
class TestCostConfig:
    """Test ModelCostConfig."""

    def test_cost_requires_max_cost(self) -> None:
        """Cost type must specify max_cost."""
        with pytest.raises(ValidationError):
            ModelCostConfig()

    def test_cost_default_per_is_request(self) -> None:
        """Default per unit is 'request'."""
        config = ModelCostConfig(max_cost=0.10)
        assert config.per == "request"

    def test_cost_accepts_per_minute(self) -> None:
        """Cost config accepts 'minute' as per unit."""
        config = ModelCostConfig(max_cost=1.00, per="minute")
        assert config.per == "minute"

    def test_cost_accepts_per_hour(self) -> None:
        """Cost config accepts 'hour' as per unit."""
        config = ModelCostConfig(max_cost=10.00, per="hour")
        assert config.per == "hour"

    def test_cost_accepts_per_day(self) -> None:
        """Cost config accepts 'day' as per unit."""
        config = ModelCostConfig(max_cost=100.00, per="day")
        assert config.per == "day"

    def test_cost_max_cost_must_be_non_negative(self) -> None:
        """max_cost cannot be negative."""
        with pytest.raises(ValidationError):
            ModelCostConfig(max_cost=-0.10)

    def test_cost_config_with_decimal_precision(self) -> None:
        """Cost config preserves decimal precision."""
        config = ModelCostConfig(max_cost=0.0001)
        assert config.max_cost == 0.0001

    def test_cost_config_serialization(self) -> None:
        """Cost config serializes correctly."""
        config = ModelCostConfig(max_cost=0.10, per="request")
        data = config.model_dump()
        assert data["max_cost"] == 0.10
        assert data["per"] == "request"


@pytest.mark.unit
class TestFieldPresenceConfig:
    """Test ModelFieldPresenceConfig."""

    def test_field_presence_requires_fields(self) -> None:
        """Fields list is required."""
        with pytest.raises(ValidationError):
            ModelFieldPresenceConfig()

    def test_field_presence_requires_non_empty_fields(self) -> None:
        """Fields list must not be empty."""
        with pytest.raises(ValidationError):
            ModelFieldPresenceConfig(fields=[])

    def test_field_presence_with_single_field(self) -> None:
        """Field presence accepts single field."""
        config = ModelFieldPresenceConfig(fields=["response"])
        assert config.fields == ["response"]

    def test_field_presence_with_multiple_fields(self) -> None:
        """Field presence accepts multiple fields."""
        config = ModelFieldPresenceConfig(fields=["response", "model", "usage"])
        assert len(config.fields) == 3
        assert "response" in config.fields
        assert "model" in config.fields
        assert "usage" in config.fields

    def test_field_presence_preserves_order(self) -> None:
        """Field presence preserves field order."""
        config = ModelFieldPresenceConfig(fields=["a", "b", "c"])
        assert config.fields == ["a", "b", "c"]

    def test_field_presence_with_nested_path(self) -> None:
        """Field presence accepts dot-notation for nested paths."""
        config = ModelFieldPresenceConfig(fields=["response.choices", "usage.tokens"])
        assert "response.choices" in config.fields

    def test_field_presence_serialization(self) -> None:
        """Field presence config serializes correctly."""
        config = ModelFieldPresenceConfig(fields=["response", "model"])
        data = config.model_dump()
        assert data["fields"] == ["response", "model"]


@pytest.mark.unit
class TestThresholdConfig:
    """Test ModelThresholdConfig."""

    def test_threshold_requires_metric_name(self) -> None:
        """Metric name is required."""
        with pytest.raises(ValidationError):
            ModelThresholdConfig()

    def test_threshold_allows_min_only(self) -> None:
        """Threshold with only min_value is valid."""
        config = ModelThresholdConfig(metric_name="accuracy", min_value=0.95)
        assert config.min_value == 0.95
        assert config.max_value is None

    def test_threshold_allows_max_only(self) -> None:
        """Threshold with only max_value is valid."""
        config = ModelThresholdConfig(metric_name="error_rate", max_value=0.05)
        assert config.max_value == 0.05
        assert config.min_value is None

    def test_threshold_allows_both_min_and_max(self) -> None:
        """Threshold with both min and max values is valid."""
        config = ModelThresholdConfig(
            metric_name="confidence",
            min_value=0.7,
            max_value=1.0,
        )
        assert config.min_value == 0.7
        assert config.max_value == 1.0

    def test_threshold_with_integer_values(self) -> None:
        """Threshold accepts integer values."""
        config = ModelThresholdConfig(metric_name="token_count", max_value=4096)
        assert config.max_value == 4096

    def test_threshold_with_negative_values(self) -> None:
        """Threshold accepts negative values for certain metrics."""
        config = ModelThresholdConfig(metric_name="log_probability", min_value=-10.0)
        assert config.min_value == -10.0

    def test_threshold_serialization(self) -> None:
        """Threshold config serializes correctly."""
        config = ModelThresholdConfig(
            metric_name="accuracy",
            min_value=0.95,
            max_value=1.0,
        )
        data = config.model_dump()
        assert data["metric_name"] == "accuracy"
        assert data["min_value"] == 0.95
        assert data["max_value"] == 1.0

    def test_threshold_requires_at_least_one_bound(self) -> None:
        """Threshold config requires at least one of min_value or max_value."""
        with pytest.raises(ValidationError) as exc_info:
            ModelThresholdConfig(metric_name="accuracy")
        assert "At least one of 'min_value' or 'max_value' must be provided" in str(
            exc_info.value
        )

    def test_threshold_rejects_min_greater_than_max(self) -> None:
        """Threshold config rejects min_value > max_value."""
        with pytest.raises(ValidationError) as exc_info:
            ModelThresholdConfig(
                metric_name="accuracy",
                min_value=1.0,
                max_value=0.5,
            )
        assert "min_value" in str(exc_info.value) and "max_value" in str(exc_info.value)


@pytest.mark.unit
class TestSchemaInvariantConfig:
    """Test ModelSchemaInvariantConfig."""

    def test_schema_requires_json_schema(self) -> None:
        """JSON schema is required."""
        with pytest.raises(ValidationError):
            ModelSchemaInvariantConfig()

    def test_schema_with_simple_type(self) -> None:
        """Schema config accepts simple type definition."""
        config = ModelSchemaInvariantConfig(json_schema={"type": "object"})
        assert config.json_schema["type"] == "object"

    def test_schema_with_required_properties(self) -> None:
        """Schema config accepts required properties."""
        schema = {
            "type": "object",
            "required": ["response"],
            "properties": {"response": {"type": "string"}},
        }
        config = ModelSchemaInvariantConfig(json_schema=schema)
        assert config.json_schema["required"] == ["response"]

    def test_schema_with_nested_objects(self) -> None:
        """Schema config accepts nested object definitions."""
        schema = {
            "type": "object",
            "properties": {
                "response": {
                    "type": "object",
                    "properties": {"content": {"type": "string"}},
                }
            },
        }
        config = ModelSchemaInvariantConfig(json_schema=schema)
        assert config.json_schema["properties"]["response"]["type"] == "object"

    def test_schema_with_array_type(self) -> None:
        """Schema config accepts array type definitions."""
        schema = {
            "type": "object",
            "properties": {"choices": {"type": "array", "items": {"type": "object"}}},
        }
        config = ModelSchemaInvariantConfig(json_schema=schema)
        assert config.json_schema["properties"]["choices"]["type"] == "array"

    def test_schema_serialization(self) -> None:
        """Schema config serializes correctly."""
        schema = {"type": "object", "required": ["response"]}
        config = ModelSchemaInvariantConfig(json_schema=schema)
        data = config.model_dump()
        assert data["json_schema"] == schema


@pytest.mark.unit
class TestFieldValueConfig:
    """Test ModelFieldValueConfig."""

    def test_field_value_requires_field_path(self) -> None:
        """Field path is required."""
        with pytest.raises(ValidationError):
            ModelFieldValueConfig()

    def test_field_value_with_expected_value(self) -> None:
        """Field value config with expected_value."""
        config = ModelFieldValueConfig(
            field_path="status",
            expected_value="success",
        )
        assert config.field_path == "status"
        assert config.expected_value == "success"

    def test_field_value_with_pattern(self) -> None:
        """Field value config with regex pattern."""
        config = ModelFieldValueConfig(
            field_path="message",
            pattern=r"success.*",
        )
        assert config.field_path == "message"
        assert config.pattern == r"success.*"

    def test_field_value_with_both(self) -> None:
        """Field value config with both expected_value and pattern."""
        config = ModelFieldValueConfig(
            field_path="status",
            expected_value="success",
            pattern=r"^success$",
        )
        assert config.expected_value == "success"
        assert config.pattern == r"^success$"

    def test_field_value_none_expected_value(self) -> None:
        """Field value config with None expected_value."""
        config = ModelFieldValueConfig(
            field_path="error",
            expected_value=None,
        )
        assert config.expected_value is None

    def test_field_value_numeric_expected_value(self) -> None:
        """Field value config with numeric expected_value."""
        config = ModelFieldValueConfig(
            field_path="score",
            expected_value=0.5,
        )
        assert config.expected_value == 0.5

    def test_field_value_nested_field_path(self) -> None:
        """Field value config with nested field path."""
        config = ModelFieldValueConfig(
            field_path="response.status.code",
            expected_value=200,
        )
        assert config.field_path == "response.status.code"

    def test_field_value_serialization(self) -> None:
        """Field value config serializes correctly."""
        config = ModelFieldValueConfig(
            field_path="status",
            expected_value="success",
        )
        data = config.model_dump()
        assert data["field_path"] == "status"
        assert data["expected_value"] == "success"


@pytest.mark.unit
class TestCustomInvariantConfig:
    """Test ModelCustomInvariantConfig."""

    def test_custom_requires_callable_path(self) -> None:
        """Callable path is required."""
        with pytest.raises(ValidationError):
            ModelCustomInvariantConfig()

    def test_custom_with_callable_path_only(self) -> None:
        """Custom config with only callable path."""
        config = ModelCustomInvariantConfig(callable_path="my_module.validator")
        assert config.callable_path == "my_module.validator"

    def test_custom_with_kwargs(self) -> None:
        """Custom config with additional keyword arguments."""
        config = ModelCustomInvariantConfig(
            callable_path="my_module.validator",
            kwargs={"threshold": 0.9, "strict": True},
        )
        assert config.callable_path == "my_module.validator"
        assert config.kwargs["threshold"] == 0.9
        assert config.kwargs["strict"] is True

    def test_custom_default_kwargs_empty(self) -> None:
        """Custom config defaults to empty kwargs."""
        config = ModelCustomInvariantConfig(callable_path="my_module.validator")
        assert config.kwargs == {}

    def test_custom_callable_path_format(self) -> None:
        """Custom config accepts module.function format."""
        config = ModelCustomInvariantConfig(
            callable_path="my_package.my_module.my_validator"
        )
        assert "my_package" in config.callable_path

    def test_custom_serialization(self) -> None:
        """Custom config serializes correctly."""
        config = ModelCustomInvariantConfig(
            callable_path="my_module.validator",
            kwargs={"key": "value"},
        )
        data = config.model_dump()
        assert data["callable_path"] == "my_module.validator"
        assert data["kwargs"]["key"] == "value"


@pytest.mark.unit
class TestConfigModelValidation:
    """Test cross-config validation behaviors."""

    def test_latency_config_type_coercion(self) -> None:
        """Latency config coerces string to int."""
        config = ModelLatencyConfig(max_ms="5000")  # type: ignore[arg-type]
        assert config.max_ms == 5000

    def test_cost_config_type_coercion(self) -> None:
        """Cost config coerces string to float."""
        config = ModelCostConfig(max_cost="0.10")  # type: ignore[arg-type]
        assert config.max_cost == 0.10

    def test_threshold_config_zero_values(self) -> None:
        """Threshold config accepts zero as valid threshold."""
        config = ModelThresholdConfig(metric_name="offset", min_value=0.0)
        assert config.min_value == 0.0

    def test_field_presence_duplicate_fields(self) -> None:
        """Field presence preserves duplicate fields (no automatic deduplication).

        The model uses a simple list[str], so duplicates are preserved as-is.
        Consumers are responsible for handling duplicates if needed.
        """
        config = ModelFieldPresenceConfig(fields=["response", "response"])
        # Duplicates are preserved - fields is a list, not a set
        assert config.fields == ["response", "response"], (
            f"Expected duplicates to be preserved, got {config.fields}"
        )
        assert len(config.fields) == 2, (
            f"Expected 2 fields (including duplicate), got {len(config.fields)}"
        )
