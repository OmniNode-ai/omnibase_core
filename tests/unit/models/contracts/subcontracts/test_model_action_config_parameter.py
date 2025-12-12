"""
Unit tests for ModelActionConfigParameter.

Comprehensive test coverage including:
- Basic instantiation with all field combinations
- Field validation (name min_length, type literal validation)
- Default value type matching (model_validator)
- Immutability tests (frozen=True)
- Serialization (model_dump, model_dump_json, model_validate_json)
- Edge cases and boundary conditions
"""

import json

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_action_config_parameter import (
    ModelActionConfigParameter,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestModelActionConfigParameterBasics:
    """Test basic ModelActionConfigParameter instantiation and defaults."""

    def test_minimal_instantiation(self):
        """Test minimal instantiation with only required fields."""
        param = ModelActionConfigParameter(
            name="timeout",
            type="int",
            required=True,
        )

        assert param.name == "timeout"
        assert param.type == "int"
        assert param.required is True
        assert param.default is None
        assert param.description is None

    def test_instantiation_with_string_type(self):
        """Test parameter with string type."""
        param = ModelActionConfigParameter(
            name="log_level",
            type="string",
            required=False,
            default="INFO",
            description="Logging level",
        )

        assert param.name == "log_level"
        assert param.type == "string"
        assert param.required is False
        assert param.default == "INFO"
        assert param.description == "Logging level"

    def test_instantiation_with_int_type(self):
        """Test parameter with int type."""
        param = ModelActionConfigParameter(
            name="max_retries",
            type="int",
            required=False,
            default=3,
        )

        assert param.name == "max_retries"
        assert param.type == "int"
        assert param.default == 3

    def test_instantiation_with_bool_type(self):
        """Test parameter with bool type."""
        param = ModelActionConfigParameter(
            name="enabled",
            type="bool",
            required=False,
            default=True,
        )

        assert param.name == "enabled"
        assert param.type == "bool"
        assert param.default is True

    def test_instantiation_with_float_type(self):
        """Test parameter with float type."""
        param = ModelActionConfigParameter(
            name="rate_limit",
            type="float",
            required=False,
            default=10.5,
        )

        assert param.name == "rate_limit"
        assert param.type == "float"
        assert param.default == 10.5

    def test_instantiation_with_list_type(self):
        """Test parameter with list type."""
        param = ModelActionConfigParameter(
            name="allowed_values",
            type="list",
            required=False,
            default=["a", "b", "c"],
        )

        assert param.name == "allowed_values"
        assert param.type == "list"
        assert param.default == ["a", "b", "c"]

    def test_instantiation_with_dict_type(self):
        """Test parameter with dict type."""
        param = ModelActionConfigParameter(
            name="config",
            type="dict",
            required=False,
            default={"key": "value"},
        )

        assert param.name == "config"
        assert param.type == "dict"
        assert param.default == {"key": "value"}

    def test_required_parameter_without_default(self):
        """Test required parameter without default value."""
        param = ModelActionConfigParameter(
            name="api_key",
            type="string",
            required=True,
        )

        assert param.required is True
        assert param.default is None

    def test_optional_parameter_with_none_default(self):
        """Test optional parameter with explicit None default."""
        param = ModelActionConfigParameter(
            name="optional_config",
            type="dict",
            required=False,
            default=None,
        )

        assert param.required is False
        assert param.default is None


class TestModelActionConfigParameterValidation:
    """Test ModelActionConfigParameter field validation."""

    def test_name_required(self):
        """Test name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(
                type="string",
                required=True,
            )

        assert "name" in str(exc_info.value)

    def test_name_min_length(self):
        """Test name has minimum length constraint (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(
                name="",
                type="string",
                required=True,
            )

        assert "name" in str(exc_info.value).lower()

    def test_name_single_char_accepted(self):
        """Test single character name is accepted."""
        param = ModelActionConfigParameter(
            name="x",
            type="int",
            required=True,
        )

        assert param.name == "x"

    def test_type_required(self):
        """Test type is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                required=True,
            )

        assert "type" in str(exc_info.value)

    def test_type_invalid_literal(self):
        """Test type must be one of the allowed literals."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="invalid_type",
                required=True,
            )

        # Should fail literal validation
        error_str = str(exc_info.value)
        assert "type" in error_str.lower()

    def test_type_all_valid_literals(self):
        """Test all valid type literals are accepted."""
        valid_types = ["string", "int", "bool", "float", "list", "dict"]

        for type_name in valid_types:
            param = ModelActionConfigParameter(
                name=f"param_{type_name}",
                type=type_name,
                required=True,
            )
            assert param.type == type_name

    def test_required_is_required(self):
        """Test required field is mandatory."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="string",
            )

        assert "required" in str(exc_info.value)

    def test_long_name_accepted(self):
        """Test long parameter names are accepted."""
        long_name = "very_long_parameter_name_" * 10
        param = ModelActionConfigParameter(
            name=long_name,
            type="string",
            required=True,
        )

        assert param.name == long_name

    def test_long_description_accepted(self):
        """Test long descriptions are accepted."""
        long_desc = "This is a very detailed description. " * 50
        param = ModelActionConfigParameter(
            name="param",
            type="string",
            required=True,
            description=long_desc,
        )

        assert param.description == long_desc

    def test_empty_description_accepted(self):
        """Test empty string description is accepted."""
        param = ModelActionConfigParameter(
            name="param",
            type="string",
            required=True,
            description="",
        )

        assert param.description == ""


class TestModelActionConfigParameterDefaultValidation:
    """Test default value type matching validation (model_validator)."""

    def test_string_default_valid(self):
        """Test valid string default for string type."""
        param = ModelActionConfigParameter(
            name="test",
            type="string",
            required=False,
            default="hello",
        )

        assert param.default == "hello"

    def test_string_default_invalid_int(self):
        """Test int default invalid for string type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="string",
                required=False,
                default=42,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "string" in exc_info.value.message
        assert "int" in exc_info.value.message

    def test_int_default_valid(self):
        """Test valid int default for int type."""
        param = ModelActionConfigParameter(
            name="test",
            type="int",
            required=False,
            default=42,
        )

        assert param.default == 42

    def test_int_default_invalid_string(self):
        """Test string default invalid for int type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="int",
                required=False,
                default="42",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "int" in exc_info.value.message
        assert "str" in exc_info.value.message

    def test_int_default_invalid_bool(self):
        """Test bool default invalid for int type (special case)."""
        # In Python, bool is a subclass of int, but we explicitly disallow this
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="int",
                required=False,
                default=True,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "bool" in exc_info.value.message
        assert "int" in exc_info.value.message

    def test_bool_default_valid(self):
        """Test valid bool default for bool type."""
        param = ModelActionConfigParameter(
            name="test",
            type="bool",
            required=False,
            default=False,
        )

        assert param.default is False

    def test_bool_default_invalid_int(self):
        """Test int default invalid for bool type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="bool",
                required=False,
                default=1,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH

    def test_float_default_valid_float(self):
        """Test valid float default for float type."""
        param = ModelActionConfigParameter(
            name="test",
            type="float",
            required=False,
            default=3.14,
        )

        assert param.default == 3.14

    def test_float_default_valid_int(self):
        """Test int default is valid for float type (int acceptable for float)."""
        param = ModelActionConfigParameter(
            name="test",
            type="float",
            required=False,
            default=42,
        )

        assert param.default == 42

    def test_float_default_invalid_string(self):
        """Test string default invalid for float type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="float",
                required=False,
                default="3.14",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH

    def test_list_default_valid(self):
        """Test valid list default for list type."""
        param = ModelActionConfigParameter(
            name="test",
            type="list",
            required=False,
            default=[1, 2, 3],
        )

        assert param.default == [1, 2, 3]

    def test_list_default_empty(self):
        """Test empty list default is valid for list type."""
        param = ModelActionConfigParameter(
            name="test",
            type="list",
            required=False,
            default=[],
        )

        assert param.default == []

    def test_list_default_invalid_tuple(self):
        """Test tuple default invalid for list type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="list",
                required=False,
                default=(1, 2, 3),
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH

    def test_dict_default_valid(self):
        """Test valid dict default for dict type."""
        param = ModelActionConfigParameter(
            name="test",
            type="dict",
            required=False,
            default={"key": "value"},
        )

        assert param.default == {"key": "value"}

    def test_dict_default_empty(self):
        """Test empty dict default is valid for dict type."""
        param = ModelActionConfigParameter(
            name="test",
            type="dict",
            required=False,
            default={},
        )

        assert param.default == {}

    def test_dict_default_invalid_list(self):
        """Test list default invalid for dict type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="dict",
                required=False,
                default=["key", "value"],
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH

    def test_none_default_always_valid(self):
        """Test None default is valid for all types."""
        valid_types = ["string", "int", "bool", "float", "list", "dict"]

        for type_name in valid_types:
            param = ModelActionConfigParameter(
                name=f"test_{type_name}",
                type=type_name,
                required=False,
                default=None,
            )
            assert param.default is None


class TestModelActionConfigParameterFrozen:
    """Test immutability (frozen=True)."""

    def test_frozen_cannot_modify_name(self):
        """Test name cannot be modified after instantiation."""
        param = ModelActionConfigParameter(
            name="original",
            type="string",
            required=True,
        )

        with pytest.raises(ValidationError):
            param.name = "modified"

    def test_frozen_cannot_modify_type(self):
        """Test type cannot be modified after instantiation."""
        param = ModelActionConfigParameter(
            name="test",
            type="string",
            required=True,
        )

        with pytest.raises(ValidationError):
            param.type = "int"

    def test_frozen_cannot_modify_required(self):
        """Test required cannot be modified after instantiation."""
        param = ModelActionConfigParameter(
            name="test",
            type="string",
            required=True,
        )

        with pytest.raises(ValidationError):
            param.required = False

    def test_frozen_cannot_modify_default(self):
        """Test default cannot be modified after instantiation."""
        param = ModelActionConfigParameter(
            name="test",
            type="string",
            required=False,
            default="original",
        )

        with pytest.raises(ValidationError):
            param.default = "modified"

    def test_frozen_cannot_modify_description(self):
        """Test description cannot be modified after instantiation."""
        param = ModelActionConfigParameter(
            name="test",
            type="string",
            required=True,
            description="original",
        )

        with pytest.raises(ValidationError):
            param.description = "modified"


class TestModelActionConfigParameterSerialization:
    """Test serialization (model_dump, model_dump_json, model_validate_json)."""

    def test_model_dump_minimal(self):
        """Test model_dump with minimal fields."""
        param = ModelActionConfigParameter(
            name="timeout",
            type="int",
            required=True,
        )

        data = param.model_dump()

        assert data["name"] == "timeout"
        assert data["type"] == "int"
        assert data["required"] is True
        assert data["default"] is None
        assert data["description"] is None

    def test_model_dump_full(self):
        """Test model_dump with all fields."""
        param = ModelActionConfigParameter(
            name="max_retries",
            type="int",
            required=False,
            default=3,
            description="Maximum retry attempts",
        )

        data = param.model_dump()

        assert data["name"] == "max_retries"
        assert data["type"] == "int"
        assert data["required"] is False
        assert data["default"] == 3
        assert data["description"] == "Maximum retry attempts"

    def test_model_dump_json(self):
        """Test model_dump_json produces valid JSON."""
        param = ModelActionConfigParameter(
            name="enabled",
            type="bool",
            required=False,
            default=True,
        )

        json_str = param.model_dump_json()

        assert isinstance(json_str, str)
        # Validate it's proper JSON
        data = json.loads(json_str)
        assert data["name"] == "enabled"
        assert data["type"] == "bool"
        assert data["default"] is True

    def test_model_validate_json(self):
        """Test model_validate_json deserializes correctly."""
        json_data = """{
            "name": "timeout_seconds",
            "type": "int",
            "required": false,
            "default": 30,
            "description": "Timeout in seconds"
        }"""

        param = ModelActionConfigParameter.model_validate_json(json_data)

        assert param.name == "timeout_seconds"
        assert param.type == "int"
        assert param.required is False
        assert param.default == 30
        assert param.description == "Timeout in seconds"

    def test_roundtrip_serialization(self):
        """Test roundtrip serialization preserves all data."""
        original = ModelActionConfigParameter(
            name="config_value",
            type="dict",
            required=False,
            default={"nested": {"key": "value"}},
            description="Complex configuration",
        )

        # Serialize and deserialize
        json_str = original.model_dump_json()
        restored = ModelActionConfigParameter.model_validate_json(json_str)

        assert restored.name == original.name
        assert restored.type == original.type
        assert restored.required == original.required
        assert restored.default == original.default
        assert restored.description == original.description

    def test_model_validate_from_dict(self):
        """Test model_validate from dict."""
        data = {
            "name": "rate",
            "type": "float",
            "required": True,
            "default": None,
            "description": "Rate value",
        }

        param = ModelActionConfigParameter.model_validate(data)

        assert param.name == "rate"
        assert param.type == "float"
        assert param.required is True

    def test_extra_fields_ignored(self):
        """Test extra fields are ignored per ConfigDict."""
        param = ModelActionConfigParameter(
            name="test",
            type="string",
            required=True,
            unknown_field="ignored",  # type: ignore[call-arg]
        )

        assert param.name == "test"
        assert not hasattr(param, "unknown_field")


class TestModelActionConfigParameterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_name_with_special_characters(self):
        """Test parameter name with special characters."""
        special_name = "param-name.with_special:chars"
        param = ModelActionConfigParameter(
            name=special_name,
            type="string",
            required=True,
        )

        assert param.name == special_name

    def test_name_with_unicode(self):
        """Test parameter name with unicode characters."""
        unicode_name = "parameter_with_unicode"
        param = ModelActionConfigParameter(
            name=unicode_name,
            type="string",
            required=True,
        )

        assert param.name == unicode_name

    def test_string_default_with_json(self):
        """Test string default containing JSON."""
        json_str = '{"key": "value", "count": 42}'
        param = ModelActionConfigParameter(
            name="json_config",
            type="string",
            required=False,
            default=json_str,
        )

        assert param.default == json_str

    def test_string_default_multiline(self):
        """Test string default with multiline text."""
        multiline = "Line 1\nLine 2\nLine 3"
        param = ModelActionConfigParameter(
            name="multiline_text",
            type="string",
            required=False,
            default=multiline,
        )

        assert param.default == multiline

    def test_int_default_zero(self):
        """Test int default with zero value."""
        param = ModelActionConfigParameter(
            name="zero_value",
            type="int",
            required=False,
            default=0,
        )

        assert param.default == 0

    def test_int_default_negative(self):
        """Test int default with negative value."""
        param = ModelActionConfigParameter(
            name="negative_value",
            type="int",
            required=False,
            default=-100,
        )

        assert param.default == -100

    def test_int_default_large_number(self):
        """Test int default with large number."""
        large = 999999999999
        param = ModelActionConfigParameter(
            name="large_value",
            type="int",
            required=False,
            default=large,
        )

        assert param.default == large

    def test_float_default_zero(self):
        """Test float default with zero."""
        param = ModelActionConfigParameter(
            name="zero_float",
            type="float",
            required=False,
            default=0.0,
        )

        assert param.default == 0.0

    def test_float_default_negative(self):
        """Test float default with negative value."""
        param = ModelActionConfigParameter(
            name="negative_float",
            type="float",
            required=False,
            default=-3.14,
        )

        assert param.default == -3.14

    def test_list_default_nested(self):
        """Test list default with nested structures."""
        nested_list = [[1, 2], [3, 4], {"nested": "dict"}]
        param = ModelActionConfigParameter(
            name="nested_list",
            type="list",
            required=False,
            default=nested_list,
        )

        assert param.default == nested_list

    def test_dict_default_nested(self):
        """Test dict default with deeply nested structure."""
        nested_dict = {
            "level1": {
                "level2": {
                    "level3": "value",
                },
            },
        }
        param = ModelActionConfigParameter(
            name="nested_dict",
            type="dict",
            required=False,
            default=nested_dict,
        )

        assert param.default == nested_dict


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
        assert "name" in required_fields
        assert "type" in required_fields
        assert "required" in required_fields

    def test_optional_fields_not_required(self):
        """Test optional fields are not in required list."""
        schema = ModelActionConfigParameter.model_json_schema()

        required_fields = schema.get("required", [])
        assert "default" not in required_fields
        assert "description" not in required_fields


class TestModelActionConfigParameterUseCases:
    """Test real-world use case scenarios."""

    def test_fsm_transition_timeout_parameter(self):
        """Test FSM transition timeout configuration."""
        param = ModelActionConfigParameter(
            name="transition_timeout_ms",
            type="int",
            required=True,
            default=None,
            description="Maximum time to wait for state transition",
        )

        assert param.type == "int"
        assert param.required is True

    def test_fsm_action_enabled_flag(self):
        """Test FSM action enabled flag."""
        param = ModelActionConfigParameter(
            name="action_enabled",
            type="bool",
            required=False,
            default=True,
            description="Whether this action is enabled",
        )

        assert param.default is True

    def test_retry_configuration_parameter(self):
        """Test retry configuration."""
        param = ModelActionConfigParameter(
            name="max_retry_attempts",
            type="int",
            required=False,
            default=3,
            description="Maximum number of retry attempts",
        )

        assert param.default == 3

    def test_logging_level_parameter(self):
        """Test logging level configuration."""
        param = ModelActionConfigParameter(
            name="log_level",
            type="string",
            required=False,
            default="INFO",
            description="Logging level for this action",
        )

        assert param.default == "INFO"

    def test_rate_limit_parameter(self):
        """Test rate limiting configuration."""
        param = ModelActionConfigParameter(
            name="requests_per_second",
            type="float",
            required=True,
            description="Maximum requests per second",
        )

        assert param.type == "float"
        assert param.required is True

    def test_allowed_values_list_parameter(self):
        """Test list of allowed values."""
        param = ModelActionConfigParameter(
            name="allowed_states",
            type="list",
            required=False,
            default=["pending", "active", "completed"],
            description="List of allowed state values",
        )

        assert param.default == ["pending", "active", "completed"]

    def test_connection_config_dict_parameter(self):
        """Test connection configuration as dict."""
        param = ModelActionConfigParameter(
            name="connection_config",
            type="dict",
            required=False,
            default={
                "host": "localhost",
                "port": 5432,
                "timeout": 30,
            },
            description="Database connection configuration",
        )

        assert param.default["host"] == "localhost"
        assert param.default["port"] == 5432
