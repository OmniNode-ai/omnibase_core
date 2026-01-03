"""Tests for invariant configuration models."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumInvariantType
from omnibase_core.models.invariant import (
    ModelCostConfig,
    ModelCustomInvariantConfig,
    ModelFieldPresenceConfig,
    ModelFieldValueConfig,
    ModelInvariantDefinition,
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

    def test_cost_max_cost_must_be_positive(self) -> None:
        """max_cost must be greater than 0 (positive), not just non-negative.

        The model intentionally uses gt=0 (greater than), not ge=0 (greater
        than or equal), because a cost limit of 0 would mean no operations
        are allowed, which is better enforced through other mechanisms
        (e.g., disabling the endpoint entirely).
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelCostConfig(max_cost=-0.10)
        assert "greater_than" in str(exc_info.value) or "greater than" in str(
            exc_info.value
        ), f"Expected 'greater than' validation error, got: {exc_info.value}"

    def test_cost_max_cost_zero_is_rejected(self) -> None:
        """max_cost=0 is rejected because cost must be strictly positive.

        This is an intentional design decision: a max_cost of 0 would mean
        'no cost allowed', which effectively disables the operation. If that
        behavior is needed, it should be handled at the operation level
        (e.g., by disabling the endpoint) rather than through cost limits.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelCostConfig(max_cost=0.0)
        error_str = str(exc_info.value)
        assert "greater than 0" in error_str or "greater_than" in error_str, (
            f"Expected validation error for max_cost=0, got: {error_str}"
        )

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

    def test_schema_rejects_empty_json_schema(self) -> None:
        """Schema config rejects empty json_schema dict."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSchemaInvariantConfig(json_schema={})
        assert "json_schema cannot be empty" in str(exc_info.value)
        assert "validation rule" in str(exc_info.value)


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

    def test_custom_rejects_path_without_dot(self) -> None:
        """Callable path must contain at least one dot."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCustomInvariantConfig(callable_path="validator")
        assert "must be a fully qualified Python path" in str(exc_info.value)
        assert "dotted notation" in str(exc_info.value)

    def test_custom_rejects_path_starting_with_dot(self) -> None:
        """Callable path cannot start with a dot."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCustomInvariantConfig(callable_path=".module.validator")
        assert "cannot start or end with a dot" in str(exc_info.value)

    def test_custom_rejects_path_ending_with_dot(self) -> None:
        """Callable path cannot end with a dot."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCustomInvariantConfig(callable_path="module.validator.")
        assert "cannot start or end with a dot" in str(exc_info.value)

    def test_custom_rejects_path_with_consecutive_dots(self) -> None:
        """Callable path cannot contain consecutive dots."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCustomInvariantConfig(callable_path="module..validator")
        assert "consecutive dots" in str(exc_info.value)

    def test_custom_rejects_path_with_invalid_identifier(self) -> None:
        """Callable path segments must be valid Python identifiers."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCustomInvariantConfig(callable_path="module.123invalid")
        assert "invalid Python identifiers" in str(exc_info.value)

    def test_custom_rejects_path_with_special_characters(self) -> None:
        """Callable path cannot contain special characters."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCustomInvariantConfig(callable_path="module.my-validator")
        assert "invalid Python identifiers" in str(exc_info.value)

    def test_custom_accepts_underscores_in_path(self) -> None:
        """Callable path accepts underscores in identifiers."""
        config = ModelCustomInvariantConfig(
            callable_path="my_module._private_validator"
        )
        assert config.callable_path == "my_module._private_validator"

    def test_custom_accepts_numbers_in_identifier(self) -> None:
        """Callable path accepts numbers after first character."""
        config = ModelCustomInvariantConfig(callable_path="module2.validator3")
        assert config.callable_path == "module2.validator3"


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
        input_fields = ["response", "response", "model", "response"]
        config = ModelFieldPresenceConfig(fields=input_fields)

        # Verify exact list equality - duplicates preserved in order
        assert config.fields == ["response", "response", "model", "response"], (
            f"Expected exact input list with duplicates preserved, got {config.fields}"
        )

        # Verify count of specific duplicates
        assert config.fields.count("response") == 3, (
            f"Expected 3 occurrences of 'response', got {config.fields.count('response')}"
        )
        assert config.fields.count("model") == 1, (
            f"Expected 1 occurrence of 'model', got {config.fields.count('model')}"
        )

        # Verify total length matches input
        assert len(config.fields) == len(input_fields), (
            f"Expected {len(input_fields)} fields, got {len(config.fields)}"
        )

        # Verify type is list (not set or other deduplicating container)
        assert type(config.fields) is list, (
            f"Expected list type, got {type(config.fields).__name__}"
        )


@pytest.mark.unit
class TestInvariantDefinitionConfigTypeMatching:
    """Test ModelInvariantDefinition config/type matching validation."""

    def test_definition_accepts_matching_latency_config(self) -> None:
        """Definition accepts ModelLatencyConfig with LATENCY type."""
        definition = ModelInvariantDefinition(
            invariant_type=EnumInvariantType.LATENCY,
            config=ModelLatencyConfig(max_ms=500),
        )
        assert definition.invariant_type == EnumInvariantType.LATENCY
        assert isinstance(definition.config, ModelLatencyConfig)

    def test_definition_accepts_matching_cost_config(self) -> None:
        """Definition accepts ModelCostConfig with COST type."""
        definition = ModelInvariantDefinition(
            invariant_type=EnumInvariantType.COST,
            config=ModelCostConfig(max_cost=1.0),
        )
        assert definition.invariant_type == EnumInvariantType.COST
        assert isinstance(definition.config, ModelCostConfig)

    def test_definition_accepts_matching_threshold_config(self) -> None:
        """Definition accepts ModelThresholdConfig with THRESHOLD type."""
        definition = ModelInvariantDefinition(
            invariant_type=EnumInvariantType.THRESHOLD,
            config=ModelThresholdConfig(metric_name="accuracy", min_value=0.9),
        )
        assert definition.invariant_type == EnumInvariantType.THRESHOLD
        assert isinstance(definition.config, ModelThresholdConfig)

    def test_definition_accepts_matching_schema_config(self) -> None:
        """Definition accepts ModelSchemaInvariantConfig with SCHEMA type."""
        definition = ModelInvariantDefinition(
            invariant_type=EnumInvariantType.SCHEMA,
            config=ModelSchemaInvariantConfig(json_schema={"type": "object"}),
        )
        assert definition.invariant_type == EnumInvariantType.SCHEMA
        assert isinstance(definition.config, ModelSchemaInvariantConfig)

    def test_definition_accepts_matching_field_presence_config(self) -> None:
        """Definition accepts ModelFieldPresenceConfig with FIELD_PRESENCE type."""
        definition = ModelInvariantDefinition(
            invariant_type=EnumInvariantType.FIELD_PRESENCE,
            config=ModelFieldPresenceConfig(fields=["response"]),
        )
        assert definition.invariant_type == EnumInvariantType.FIELD_PRESENCE
        assert isinstance(definition.config, ModelFieldPresenceConfig)

    def test_definition_accepts_matching_field_value_config(self) -> None:
        """Definition accepts ModelFieldValueConfig with FIELD_VALUE type."""
        definition = ModelInvariantDefinition(
            invariant_type=EnumInvariantType.FIELD_VALUE,
            config=ModelFieldValueConfig(field_path="status"),
        )
        assert definition.invariant_type == EnumInvariantType.FIELD_VALUE
        assert isinstance(definition.config, ModelFieldValueConfig)

    def test_definition_accepts_matching_custom_config(self) -> None:
        """Definition accepts ModelCustomInvariantConfig with CUSTOM type."""
        definition = ModelInvariantDefinition(
            invariant_type=EnumInvariantType.CUSTOM,
            config=ModelCustomInvariantConfig(callable_path="my_module.validator"),
        )
        assert definition.invariant_type == EnumInvariantType.CUSTOM
        assert isinstance(definition.config, ModelCustomInvariantConfig)

    def test_definition_rejects_mismatched_latency_type_with_cost_config(self) -> None:
        """Definition rejects ModelCostConfig with LATENCY type."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantDefinition(
                invariant_type=EnumInvariantType.LATENCY,
                config=ModelCostConfig(max_cost=1.0),
            )
        assert "Config type mismatch" in str(exc_info.value)
        assert "ModelLatencyConfig" in str(exc_info.value)
        assert "ModelCostConfig" in str(exc_info.value)

    def test_definition_rejects_mismatched_cost_type_with_latency_config(self) -> None:
        """Definition rejects ModelLatencyConfig with COST type."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantDefinition(
                invariant_type=EnumInvariantType.COST,
                config=ModelLatencyConfig(max_ms=500),
            )
        assert "Config type mismatch" in str(exc_info.value)
        assert "ModelCostConfig" in str(exc_info.value)
        assert "ModelLatencyConfig" in str(exc_info.value)

    def test_definition_rejects_mismatched_schema_type_with_threshold_config(
        self,
    ) -> None:
        """Definition rejects ModelThresholdConfig with SCHEMA type."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantDefinition(
                invariant_type=EnumInvariantType.SCHEMA,
                config=ModelThresholdConfig(metric_name="accuracy", min_value=0.9),
            )
        assert "Config type mismatch" in str(exc_info.value)
        assert "ModelSchemaInvariantConfig" in str(exc_info.value)

    def test_definition_error_message_includes_expected_type(self) -> None:
        """Config mismatch error message includes expected config type."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantDefinition(
                invariant_type=EnumInvariantType.CUSTOM,
                config=ModelLatencyConfig(max_ms=100),
            )
        error_str = str(exc_info.value)
        assert "ModelCustomInvariantConfig" in error_str
        assert "custom" in error_str.lower()

    def test_definition_serialization(self) -> None:
        """Definition serializes correctly."""
        definition = ModelInvariantDefinition(
            invariant_type=EnumInvariantType.LATENCY,
            config=ModelLatencyConfig(max_ms=500),
        )
        data = definition.model_dump()
        assert data["invariant_type"] == "latency"
        assert data["config"]["max_ms"] == 500
