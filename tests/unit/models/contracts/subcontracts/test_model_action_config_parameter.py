"""
Unit tests for ModelActionConfigParameter and ModelActionConfigValue.

Comprehensive test coverage including:
- ModelActionConfigParameter field validation
- ModelActionConfigValue discriminated union behavior
- ModelActionConfigStringValue, ModelActionConfigNumericValue, ModelActionConfigBooleanValue
- Factory functions (from_string, from_int, from_float, from_bool, from_value)
- Type conversions (as_string, as_int, as_float, as_bool)
- Discriminator validation
- Edge cases and error scenarios
- ConfigDict behavior
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.contracts.model_action_config_parameter import (
    ModelActionConfigParameter,
)
from omnibase_core.models.core.model_action_config_value import (
    ModelActionConfigBooleanValue,
    ModelActionConfigNumericValue,
    ModelActionConfigStringValue,
    from_bool,
    from_float,
    from_int,
    from_numeric,
    from_string,
    from_value,
    get_action_config_discriminator_value,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class TestModelActionConfigParameterBasics:
    """Test basic ModelActionConfigParameter instantiation and defaults."""

    def test_minimal_instantiation_string_value(self):
        """Test parameter with string value."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="timeout",
            parameter_value=from_string("30s"),
        )

        assert param.parameter_name == "timeout"
        assert isinstance(param.parameter_value, ModelActionConfigStringValue)
        assert param.parameter_value.value == "30s"
        assert param.is_required is False
        assert param.description is None
        assert param.validation_rule is None

    def test_minimal_instantiation_numeric_value(self):
        """Test parameter with numeric value."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="max_retries",
            parameter_value=from_int(5),
        )

        assert param.parameter_name == "max_retries"
        assert isinstance(param.parameter_value, ModelActionConfigNumericValue)
        assert param.parameter_value.as_int() == 5

    def test_minimal_instantiation_boolean_value(self):
        """Test parameter with boolean value."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="enabled",
            parameter_value=from_bool(True),
        )

        assert param.parameter_name == "enabled"
        assert isinstance(param.parameter_value, ModelActionConfigBooleanValue)
        assert param.parameter_value.as_bool() is True

    def test_full_instantiation(self):
        """Test parameter with all fields specified."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="connection_timeout",
            parameter_value=from_int(30),
            is_required=True,
            description="Maximum time to wait for connection",
            validation_rule="value > 0 and value <= 300",
        )

        assert param.parameter_name == "connection_timeout"
        assert param.parameter_value.as_int() == 30
        assert param.is_required is True
        assert param.description == "Maximum time to wait for connection"
        assert param.validation_rule == "value > 0 and value <= 300"

    def test_default_is_required(self):
        """Test is_required defaults to False."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="optional_param",
            parameter_value=from_string("default"),
        )

        assert param.is_required is False

    def test_default_description_none(self):
        """Test description defaults to None."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="param",
            parameter_value=from_string("value"),
        )

        assert param.description is None

    def test_default_validation_rule_none(self):
        """Test validation_rule defaults to None."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="param",
            parameter_value=from_string("value"),
        )

        assert param.validation_rule is None


class TestModelActionConfigParameterValidation:
    """Test ModelActionConfigParameter field validation."""

    def test_parameter_name_required(self):
        """Test parameter_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(
                version=DEFAULT_VERSION,
                parameter_value=from_string("value"),
            )

        assert "parameter_name" in str(exc_info.value)

    def test_parameter_name_min_length(self):
        """Test parameter_name has minimum length constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(
                version=DEFAULT_VERSION,
                parameter_name="",
                parameter_value=from_string("value"),
            )

        assert "parameter_name" in str(exc_info.value)

    def test_parameter_name_whitespace_accepted(self):
        """Test parameter_name accepts whitespace (no strip validation)."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="   ",
            parameter_value=from_string("value"),
        )
        # Pydantic doesn't strip by default, so whitespace is accepted
        assert param.parameter_name == "   "

    def test_parameter_value_required(self):
        """Test parameter_value is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(version=DEFAULT_VERSION, parameter_name="test")

        assert "parameter_value" in str(exc_info.value)

    def test_long_parameter_name(self):
        """Test parameter_name accepts long names."""
        long_name = "very_long_parameter_name_" * 10
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name=long_name,
            parameter_value=from_string("value"),
        )

        assert param.parameter_name == long_name

    def test_long_description(self):
        """Test description accepts long text."""
        long_desc = "This is a very detailed description. " * 50
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="param",
            parameter_value=from_string("value"),
            description=long_desc,
        )

        assert param.description == long_desc

    def test_empty_description_accepted(self):
        """Test empty string description is accepted."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="param",
            parameter_value=from_string("value"),
            description="",
        )

        assert param.description == ""


class TestModelActionConfigStringValue:
    """Test ModelActionConfigStringValue behavior."""

    def test_string_value_creation(self):
        """Test creating string value."""
        value = from_string("hello")

        assert isinstance(value, ModelActionConfigStringValue)
        assert value.value_type == "string"
        assert value.value == "hello"

    def test_string_value_to_python(self):
        """Test to_python_value returns string."""
        value = from_string("test")

        assert value.to_python_value() == "test"
        assert isinstance(value.to_python_value(), str)

    def test_string_value_as_string(self):
        """Test as_string returns string."""
        value = from_string("data")

        assert value.as_string() == "data"

    def test_string_value_as_int_valid(self):
        """Test as_int converts valid numeric string."""
        value = from_string("42")

        assert value.as_int() == 42

    def test_string_value_as_int_invalid(self):
        """Test as_int raises error for non-numeric string."""
        value = from_string("not_a_number")

        with pytest.raises(ModelOnexError) as exc_info:
            value.as_int()

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Cannot convert string" in exc_info.value.message

    def test_string_value_empty(self):
        """Test string value with empty string."""
        value = from_string("")

        assert value.value == ""
        assert value.as_string() == ""

    def test_string_value_whitespace(self):
        """Test string value with whitespace."""
        value = from_string("  spaces  ")

        assert value.value == "  spaces  "

    def test_string_value_multiline(self):
        """Test string value with multiline text."""
        multiline = "Line 1\nLine 2\nLine 3"
        value = from_string(multiline)

        assert value.value == multiline


class TestModelActionConfigNumericValue:
    """Test ModelActionConfigNumericValue behavior."""

    def test_numeric_value_from_int(self):
        """Test creating numeric value from int."""
        value = from_int(42)

        assert isinstance(value, ModelActionConfigNumericValue)
        assert value.value_type == "numeric"
        assert value.to_python_value() == 42

    def test_numeric_value_from_float(self):
        """Test creating numeric value from float."""
        value = from_float(3.14)

        assert isinstance(value, ModelActionConfigNumericValue)
        assert value.value_type == "numeric"
        assert value.to_python_value() == 3.14

    def test_numeric_value_from_numeric(self):
        """Test creating numeric value from ModelNumericValue."""
        numeric = ModelNumericValue.from_int(100)
        value = from_numeric(numeric)

        assert isinstance(value, ModelActionConfigNumericValue)
        assert value.to_python_value() == 100

    def test_numeric_value_as_int(self):
        """Test as_int returns integer."""
        value = from_int(42)

        assert value.as_int() == 42
        assert isinstance(value.as_int(), int)

    def test_numeric_value_as_float(self):
        """Test as_float returns float."""
        value = from_float(3.14)

        assert value.as_float() == 3.14
        assert isinstance(value.as_float(), float)

    def test_numeric_value_as_string(self):
        """Test as_string returns string representation."""
        value = from_int(42)

        assert value.as_string() == "42"
        assert isinstance(value.as_string(), str)

    def test_numeric_value_zero(self):
        """Test numeric value with zero."""
        value = from_int(0)

        assert value.to_python_value() == 0
        assert value.as_int() == 0

    def test_numeric_value_negative(self):
        """Test numeric value with negative number."""
        value = from_int(-100)

        assert value.to_python_value() == -100
        assert value.as_int() == -100

    def test_numeric_value_large_number(self):
        """Test numeric value with large number."""
        large = 999999999999
        value = from_int(large)

        assert value.to_python_value() == large


class TestModelActionConfigBooleanValue:
    """Test ModelActionConfigBooleanValue behavior."""

    def test_boolean_value_true(self):
        """Test creating boolean value True."""
        value = from_bool(True)

        assert isinstance(value, ModelActionConfigBooleanValue)
        assert value.value_type == "boolean"
        assert value.value is True

    def test_boolean_value_false(self):
        """Test creating boolean value False."""
        value = from_bool(False)

        assert isinstance(value, ModelActionConfigBooleanValue)
        assert value.value_type == "boolean"
        assert value.value is False

    def test_boolean_value_to_python(self):
        """Test to_python_value returns bool."""
        value = from_bool(True)

        assert value.to_python_value() is True
        assert isinstance(value.to_python_value(), bool)

    def test_boolean_value_as_bool(self):
        """Test as_bool returns boolean."""
        value = from_bool(False)

        assert value.as_bool() is False

    def test_boolean_value_as_string_true(self):
        """Test as_string returns 'true' for True."""
        value = from_bool(True)

        assert value.as_string() == "true"

    def test_boolean_value_as_string_false(self):
        """Test as_string returns 'false' for False."""
        value = from_bool(False)

        assert value.as_string() == "false"


class TestActionConfigValueFactoryFunctions:
    """Test factory functions for creating action config values."""

    def test_from_value_string(self):
        """Test from_value with string input."""
        value = from_value("hello")

        assert isinstance(value, ModelActionConfigStringValue)
        assert value.value == "hello"

    def test_from_value_int(self):
        """Test from_value with int input."""
        value = from_value(42)

        assert isinstance(value, ModelActionConfigNumericValue)
        assert value.as_int() == 42

    def test_from_value_float(self):
        """Test from_value with float input."""
        value = from_value(3.14)

        assert isinstance(value, ModelActionConfigNumericValue)
        assert value.as_float() == 3.14

    def test_from_value_bool_true(self):
        """Test from_value with bool True (must check before int)."""
        value = from_value(True)

        assert isinstance(value, ModelActionConfigBooleanValue)
        assert value.as_bool() is True

    def test_from_value_bool_false(self):
        """Test from_value with bool False."""
        value = from_value(False)

        assert isinstance(value, ModelActionConfigBooleanValue)
        assert value.as_bool() is False

    def test_from_value_fallback_to_string(self):
        """Test from_value falls back to string for unknown types."""
        value = from_value({"key": "value"})

        assert isinstance(value, ModelActionConfigStringValue)
        assert "key" in value.value

    def test_from_value_none_becomes_string(self):
        """Test from_value converts None to string."""
        value = from_value(None)

        assert isinstance(value, ModelActionConfigStringValue)
        assert value.value == "None"


class TestActionConfigValueDiscriminator:
    """Test discriminator function behavior."""

    def test_discriminator_string_dict(self):
        """Test discriminator with string type in dict."""
        result = get_action_config_discriminator_value({"value_type": "string"})

        assert result == "string"

    def test_discriminator_numeric_dict(self):
        """Test discriminator with numeric type in dict."""
        result = get_action_config_discriminator_value({"value_type": "numeric"})

        assert result == "numeric"

    def test_discriminator_boolean_dict(self):
        """Test discriminator with boolean type in dict."""
        result = get_action_config_discriminator_value({"value_type": "boolean"})

        assert result == "boolean"

    def test_discriminator_missing_value_type(self):
        """Test discriminator defaults to string when missing."""
        result = get_action_config_discriminator_value({})

        assert result == "string"

    def test_discriminator_object_with_attribute(self):
        """Test discriminator with object having value_type attribute."""
        value = from_int(42)
        result = get_action_config_discriminator_value(value)

        assert result == "numeric"

    def test_discriminator_object_without_attribute(self):
        """Test discriminator defaults to string for object without attribute."""

        class CustomObject:
            pass

        obj = CustomObject()
        result = get_action_config_discriminator_value(obj)

        assert result == "string"


class TestModelActionConfigParameterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_required_parameter_with_validation(self):
        """Test required parameter with validation rule."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="port",
            parameter_value=from_int(8080),
            is_required=True,
            validation_rule="1024 <= value <= 65535",
        )

        assert param.is_required is True
        assert param.validation_rule is not None

    def test_optional_parameter_with_default(self):
        """Test optional parameter with default value."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="timeout",
            parameter_value=from_int(30),
            is_required=False,
            description="Defaults to 30 seconds",
        )

        assert param.is_required is False
        assert "default" in param.description.lower()

    def test_complex_validation_rule(self):
        """Test parameter with complex validation rule."""
        rule = "value in ['DEBUG', 'INFO', 'WARNING', 'ERROR'] and len(value) > 0"
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="log_level",
            parameter_value=from_string("INFO"),
            validation_rule=rule,
        )

        assert param.validation_rule == rule

    def test_parameter_with_json_string_value(self):
        """Test parameter with JSON string value."""
        json_str = '{"key": "value", "count": 42}'
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="config",
            parameter_value=from_string(json_str),
        )

        assert param.parameter_value.value == json_str

    def test_parameter_with_numeric_string(self):
        """Test parameter with numeric string value."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="version",
            parameter_value=from_string("1.2.3"),
        )

        assert isinstance(param.parameter_value, ModelActionConfigStringValue)
        assert param.parameter_value.value == "1.2.3"

    def test_parameter_name_with_special_chars(self):
        """Test parameter_name with special characters."""
        special_name = "param-name.with_special:chars"
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name=special_name,
            parameter_value=from_string("value"),
        )

        assert param.parameter_name == special_name


class TestModelActionConfigParameterConfigDict:
    """Test ConfigDict behavior."""

    def test_extra_fields_ignored(self):
        """Test extra fields are ignored per ConfigDict."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="test",
            parameter_value=from_string("value"),
            unknown_field="ignored",  # type: ignore[call-arg]
        )

        assert param.parameter_name == "test"
        assert not hasattr(param, "unknown_field")

    def test_validate_assignment(self):
        """Test assignment validation is enabled."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="test",
            parameter_value=from_string("value"),
        )

        # Valid assignment
        param.is_required = True
        assert param.is_required is True

        # Invalid assignment should raise
        with pytest.raises(ValidationError):
            param.parameter_name = ""

    def test_use_enum_values_false(self):
        """Test use_enum_values=False in nested models."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="test",
            parameter_value=from_string("value"),
        )

        # Value type should be preserved as string
        assert param.parameter_value.value_type == "string"

    def test_model_serialization(self):
        """Test parameter model serialization."""
        original = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="max_connections",
            parameter_value=from_int(100),
            is_required=True,
            description="Maximum number of concurrent connections",
            validation_rule="value > 0",
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize
        restored = ModelActionConfigParameter(**data)

        assert restored.parameter_name == original.parameter_name
        assert restored.parameter_value.as_int() == original.parameter_value.as_int()
        assert restored.is_required == original.is_required
        assert restored.description == original.description
        assert restored.validation_rule == original.validation_rule

    def test_model_json_serialization(self):
        """Test parameter JSON serialization."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="enabled",
            parameter_value=from_bool(True),
        )

        json_str = param.model_dump_json()
        assert isinstance(json_str, str)
        assert "enabled" in json_str

    def test_model_json_deserialization(self):
        """Test parameter JSON deserialization."""
        json_data = """{
            "version": {"major": 1, "minor": 0, "patch": 0},
            "parameter_name": "timeout",
            "parameter_value": {
                "value_type": "numeric",
                "value": {"value_type": "integer", "value": 30}
            },
            "is_required": true
        }"""

        param = ModelActionConfigParameter.model_validate_json(json_data)

        assert param.parameter_name == "timeout"
        assert param.parameter_value.as_int() == 30
        assert param.is_required is True


class TestModelActionConfigParameterDocumentation:
    """Test documentation and interface guarantees."""

    def test_docstring_present(self):
        """Test model has docstring."""
        assert ModelActionConfigParameter.__doc__ is not None
        assert len(ModelActionConfigParameter.__doc__) > 20

    def test_field_descriptions(self):
        """Test all fields have descriptions."""
        schema = ModelActionConfigParameter.model_json_schema()

        for field_name, field_info in schema.get("properties", {}).items():
            assert "description" in field_info, (
                f"Field {field_name} missing description"
            )

    def test_required_fields_documented(self):
        """Test required fields are properly documented in schema."""
        schema = ModelActionConfigParameter.model_json_schema()

        required_fields = schema.get("required", [])
        assert "parameter_name" in required_fields
        assert "parameter_value" in required_fields

    def test_optional_fields_documented(self):
        """Test optional fields are not in required list."""
        schema = ModelActionConfigParameter.model_json_schema()

        required_fields = schema.get("required", [])
        assert "is_required" not in required_fields
        assert "description" not in required_fields
        assert "validation_rule" not in required_fields


class TestModelActionConfigParameterUseCases:
    """Test real-world use case scenarios."""

    def test_fsm_transition_timeout_parameter(self):
        """Test FSM transition timeout configuration."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="transition_timeout_ms",
            parameter_value=from_int(5000),
            is_required=True,
            description="Maximum time to wait for state transition",
            validation_rule="value > 0 and value <= 60000",
        )

        assert param.parameter_value.as_int() == 5000
        assert param.is_required is True

    def test_fsm_action_enabled_flag(self):
        """Test FSM action enabled flag."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="action_enabled",
            parameter_value=from_bool(True),
            is_required=False,
            description="Whether this action is enabled",
        )

        assert param.parameter_value.as_bool() is True

    def test_retry_configuration_parameter(self):
        """Test retry configuration."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="max_retry_attempts",
            parameter_value=from_int(3),
            is_required=True,
            description="Maximum number of retry attempts",
            validation_rule="value >= 0 and value <= 10",
        )

        assert param.parameter_value.as_int() == 3

    def test_logging_level_parameter(self):
        """Test logging level configuration."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="log_level",
            parameter_value=from_string("INFO"),
            is_required=False,
            description="Logging level for this action",
            validation_rule="value in ['DEBUG', 'INFO', 'WARNING', 'ERROR']",
        )

        assert param.parameter_value.as_string() == "INFO"

    def test_rate_limit_parameter(self):
        """Test rate limiting configuration."""
        param = ModelActionConfigParameter(
            version=DEFAULT_VERSION,
            parameter_name="requests_per_second",
            parameter_value=from_float(10.5),
            is_required=True,
            description="Maximum requests per second",
            validation_rule="value > 0",
        )

        assert param.parameter_value.as_float() == 10.5
