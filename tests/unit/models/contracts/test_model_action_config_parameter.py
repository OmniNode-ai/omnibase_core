"""
Comprehensive unit tests for ModelActionConfigParameter.

Tests the ModelActionConfigParameter model which defines strongly-typed
parameters for action configuration in FSM transitions. This model is
a key component of the NodeReducer FSM contract system.

Test Categories:
1. Minimal Instantiation Tests - Required fields only
2. Full Instantiation Tests - All fields populated
3. Parameter Type Tests - Each supported type (string, int, bool, float, list, dict)
4. Type Validation Tests - Default value type matching
5. Required vs Optional Tests - Parameter requirement semantics
6. Serialization Tests - model_dump/model_validate roundtrip
7. Edge Cases - Boundary conditions and special values
8. Error Handling Tests - Invalid inputs and error messages

See Also:
    - docs/specs/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md: NodeReducer contract specification
    - ModelFSMTransitionAction: Uses ModelActionConfigParameter for action parameters
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_action_config_parameter import (
    ModelActionConfigParameter,
    ParameterType,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# =============================================================================
# SECTION 1: Minimal Instantiation Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionConfigParameterMinimal:
    """Tests for minimal instantiation with required fields only."""

    def test_minimal_instantiation_required_true(self) -> None:
        """Test minimal instantiation with required=True."""
        param = ModelActionConfigParameter(
            name="test_param",
            type="string",
            required=True,
        )
        assert param.name == "test_param"
        assert param.type == "string"
        assert param.required is True
        assert param.default is None
        assert param.description is None

    def test_minimal_instantiation_required_false(self) -> None:
        """Test minimal instantiation with required=False."""
        param = ModelActionConfigParameter(
            name="optional_param",
            type="int",
            required=False,
        )
        assert param.name == "optional_param"
        assert param.type == "int"
        assert param.required is False
        assert param.default is None
        assert param.description is None

    def test_minimal_missing_name_fails(self) -> None:
        """Test that missing name field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(
                type="string",
                required=True,
            )  # type: ignore[call-arg]
        assert "name" in str(exc_info.value).lower()

    def test_minimal_missing_type_fails(self) -> None:
        """Test that missing type field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(
                name="test_param",
                required=True,
            )  # type: ignore[call-arg]
        assert "type" in str(exc_info.value).lower()

    def test_minimal_missing_required_fails(self) -> None:
        """Test that missing required field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(
                name="test_param",
                type="string",
            )  # type: ignore[call-arg]
        assert "required" in str(exc_info.value).lower()


# =============================================================================
# SECTION 2: Full Instantiation Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionConfigParameterFull:
    """Tests for full instantiation with all fields populated."""

    def test_full_instantiation_string_type(self) -> None:
        """Test full instantiation with string type and all fields."""
        param = ModelActionConfigParameter(
            name="message",
            type="string",
            required=False,
            default="Hello",
            description="A greeting message",
        )
        assert param.name == "message"
        assert param.type == "string"
        assert param.required is False
        assert param.default == "Hello"
        assert param.description == "A greeting message"

    def test_full_instantiation_int_type(self) -> None:
        """Test full instantiation with int type and all fields."""
        param = ModelActionConfigParameter(
            name="timeout_seconds",
            type="int",
            required=False,
            default=30,
            description="Timeout for the operation in seconds",
        )
        assert param.name == "timeout_seconds"
        assert param.type == "int"
        assert param.required is False
        assert param.default == 30
        assert param.description == "Timeout for the operation in seconds"

    def test_full_instantiation_bool_type(self) -> None:
        """Test full instantiation with bool type and all fields."""
        param = ModelActionConfigParameter(
            name="enable_logging",
            type="bool",
            required=False,
            default=True,
            description="Whether to enable logging",
        )
        assert param.name == "enable_logging"
        assert param.type == "bool"
        assert param.required is False
        assert param.default is True
        assert param.description == "Whether to enable logging"

    def test_full_instantiation_float_type(self) -> None:
        """Test full instantiation with float type and all fields."""
        param = ModelActionConfigParameter(
            name="threshold",
            type="float",
            required=False,
            default=0.95,
            description="Confidence threshold",
        )
        assert param.name == "threshold"
        assert param.type == "float"
        assert param.required is False
        assert param.default == 0.95
        assert param.description == "Confidence threshold"

    def test_full_instantiation_list_type(self) -> None:
        """Test full instantiation with list type and all fields."""
        param = ModelActionConfigParameter(
            name="tags",
            type="list",
            required=False,
            default=["tag1", "tag2"],
            description="List of tags",
        )
        assert param.name == "tags"
        assert param.type == "list"
        assert param.required is False
        assert param.default == ["tag1", "tag2"]
        assert param.description == "List of tags"

    def test_full_instantiation_dict_type(self) -> None:
        """Test full instantiation with dict type and all fields."""
        param = ModelActionConfigParameter(
            name="metadata",
            type="dict",
            required=False,
            default={"key": "value"},
            description="Additional metadata",
        )
        assert param.name == "metadata"
        assert param.type == "dict"
        assert param.required is False
        assert param.default == {"key": "value"}
        assert param.description == "Additional metadata"


# =============================================================================
# SECTION 3: Parameter Type Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionConfigParameterTypes:
    """Tests for each supported parameter type."""

    @pytest.mark.parametrize(
        "param_type",
        ["string", "int", "bool", "float", "list", "dict"],
    )
    def test_valid_parameter_types(self, param_type: ParameterType) -> None:
        """Test that all valid parameter types are accepted."""
        param = ModelActionConfigParameter(
            name="test_param",
            type=param_type,
            required=True,
        )
        assert param.type == param_type

    def test_invalid_parameter_type_fails(self) -> None:
        """Test that invalid parameter type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(
                name="test_param",
                type="invalid_type",  # type: ignore[arg-type]
                required=True,
            )
        assert "type" in str(exc_info.value).lower()

    def test_parameter_type_case_sensitive(self) -> None:
        """Test that parameter types are case-sensitive."""
        with pytest.raises(ValidationError):
            ModelActionConfigParameter(
                name="test_param",
                type="String",  # type: ignore[arg-type]
                required=True,
            )

    def test_parameter_type_empty_string_fails(self) -> None:
        """Test that empty string type fails."""
        with pytest.raises(ValidationError):
            ModelActionConfigParameter(
                name="test_param",
                type="",  # type: ignore[arg-type]
                required=True,
            )


# =============================================================================
# SECTION 4: Type Validation Tests - Default Value Matching
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionConfigParameterTypeValidation:
    """Tests for default value type validation."""

    def test_string_default_matches_string_type(self) -> None:
        """Test that string default matches string type."""
        param = ModelActionConfigParameter(
            name="test",
            type="string",
            required=False,
            default="hello",
        )
        assert param.default == "hello"

    def test_int_default_matches_int_type(self) -> None:
        """Test that int default matches int type."""
        param = ModelActionConfigParameter(
            name="test",
            type="int",
            required=False,
            default=42,
        )
        assert param.default == 42

    def test_bool_default_matches_bool_type(self) -> None:
        """Test that bool default matches bool type."""
        param = ModelActionConfigParameter(
            name="test",
            type="bool",
            required=False,
            default=True,
        )
        assert param.default is True

    def test_float_default_matches_float_type(self) -> None:
        """Test that float default matches float type."""
        param = ModelActionConfigParameter(
            name="test",
            type="float",
            required=False,
            default=3.14,
        )
        assert param.default == 3.14

    def test_int_default_acceptable_for_float_type(self) -> None:
        """Test that int default is acceptable for float type."""
        param = ModelActionConfigParameter(
            name="test",
            type="float",
            required=False,
            default=42,  # int is acceptable for float
        )
        assert param.default == 42

    def test_list_default_matches_list_type(self) -> None:
        """Test that list default matches list type."""
        param = ModelActionConfigParameter(
            name="test",
            type="list",
            required=False,
            default=[1, 2, 3],
        )
        assert param.default == [1, 2, 3]

    def test_dict_default_matches_dict_type(self) -> None:
        """Test that dict default matches dict type."""
        param = ModelActionConfigParameter(
            name="test",
            type="dict",
            required=False,
            default={"a": 1},
        )
        assert param.default == {"a": 1}

    def test_string_default_mismatch_int_type_fails(self) -> None:
        """Test that string default with int type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="int",
                required=False,
                default="not_an_int",
            )
        assert "type" in str(exc_info.value).lower()
        assert (
            "mismatch" in str(exc_info.value).lower()
            or "int" in str(exc_info.value).lower()
        )

    def test_int_default_mismatch_string_type_fails(self) -> None:
        """Test that int default with string type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="string",
                required=False,
                default=42,
            )
        assert "type" in str(exc_info.value).lower()

    def test_bool_default_mismatch_int_type_fails(self) -> None:
        """Test that bool default with int type raises error.

        This tests the special case where bool is a subclass of int in Python.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="int",
                required=False,
                default=True,  # bool is subclass of int, but should be rejected
            )
        assert "bool" in str(exc_info.value).lower()

    def test_string_default_mismatch_bool_type_fails(self) -> None:
        """Test that string default with bool type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="bool",
                required=False,
                default="true",
            )
        assert "type" in str(exc_info.value).lower()

    def test_string_default_mismatch_list_type_fails(self) -> None:
        """Test that string default with list type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="list",
                required=False,
                default="not_a_list",
            )
        assert "type" in str(exc_info.value).lower()

    def test_list_default_mismatch_dict_type_fails(self) -> None:
        """Test that list default with dict type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="dict",
                required=False,
                default=[1, 2, 3],
            )
        assert "type" in str(exc_info.value).lower()


# =============================================================================
# SECTION 5: Required vs Optional Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionConfigParameterRequired:
    """Tests for required vs optional parameter semantics."""

    def test_required_true_no_default(self) -> None:
        """Test required parameter without default value."""
        param = ModelActionConfigParameter(
            name="required_param",
            type="string",
            required=True,
        )
        assert param.required is True
        assert param.default is None

    def test_required_false_with_default(self) -> None:
        """Test optional parameter with default value."""
        param = ModelActionConfigParameter(
            name="optional_param",
            type="int",
            required=False,
            default=10,
        )
        assert param.required is False
        assert param.default == 10

    def test_required_true_with_default(self) -> None:
        """Test required parameter can also have a default value.

        This is a valid scenario - the default provides documentation
        of a typical value, but the caller must still provide a value.
        """
        param = ModelActionConfigParameter(
            name="required_with_default",
            type="string",
            required=True,
            default="example",
        )
        assert param.required is True
        assert param.default == "example"

    def test_required_false_no_default(self) -> None:
        """Test optional parameter without default value."""
        param = ModelActionConfigParameter(
            name="optional_no_default",
            type="bool",
            required=False,
        )
        assert param.required is False
        assert param.default is None


# =============================================================================
# SECTION 6: Serialization Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionConfigParameterSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump_minimal(self) -> None:
        """Test model_dump with minimal instantiation."""
        param = ModelActionConfigParameter(
            name="test",
            type="string",
            required=True,
        )
        dumped = param.model_dump()
        assert dumped["name"] == "test"
        assert dumped["type"] == "string"
        assert dumped["required"] is True
        assert dumped["default"] is None
        assert dumped["description"] is None

    def test_model_dump_full(self) -> None:
        """Test model_dump with all fields."""
        param = ModelActionConfigParameter(
            name="count",
            type="int",
            required=False,
            default=5,
            description="Item count",
        )
        dumped = param.model_dump()
        assert dumped["name"] == "count"
        assert dumped["type"] == "int"
        assert dumped["required"] is False
        assert dumped["default"] == 5
        assert dumped["description"] == "Item count"

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate from dictionary."""
        data = {
            "name": "enabled",
            "type": "bool",
            "required": False,
            "default": True,
            "description": "Enable feature",
        }
        param = ModelActionConfigParameter.model_validate(data)
        assert param.name == "enabled"
        assert param.type == "bool"
        assert param.required is False
        assert param.default is True
        assert param.description == "Enable feature"

    def test_roundtrip_serialization_string(self) -> None:
        """Test roundtrip serialization for string type."""
        original = ModelActionConfigParameter(
            name="message",
            type="string",
            required=False,
            default="hello",
            description="A message",
        )
        dumped = original.model_dump()
        restored = ModelActionConfigParameter.model_validate(dumped)
        assert restored.name == original.name
        assert restored.type == original.type
        assert restored.required == original.required
        assert restored.default == original.default
        assert restored.description == original.description

    def test_roundtrip_serialization_complex_default(self) -> None:
        """Test roundtrip serialization with complex default values."""
        original = ModelActionConfigParameter(
            name="config",
            type="dict",
            required=False,
            default={"nested": {"key": "value"}, "list": [1, 2, 3]},
            description="Complex config",
        )
        dumped = original.model_dump()
        restored = ModelActionConfigParameter.model_validate(dumped)
        assert restored.default == original.default

    def test_model_dump_json_mode(self) -> None:
        """Test model_dump with mode='json' for JSON-compatible output."""
        param = ModelActionConfigParameter(
            name="items",
            type="list",
            required=False,
            default=[1, 2, 3],
        )
        dumped = param.model_dump(mode="json")
        # Should be JSON-serializable
        import json

        json_str = json.dumps(dumped)
        assert json_str is not None


# =============================================================================
# SECTION 7: Edge Cases
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionConfigParameterEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_name_fails(self) -> None:
        """Test that empty name fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionConfigParameter(
                name="",
                type="string",
                required=True,
            )
        assert "name" in str(exc_info.value).lower()

    def test_single_char_name_valid(self) -> None:
        """Test that single character name is valid."""
        param = ModelActionConfigParameter(
            name="x",
            type="int",
            required=True,
        )
        assert param.name == "x"

    def test_long_name_valid(self) -> None:
        """Test that long name is valid."""
        long_name = "a" * 1000
        param = ModelActionConfigParameter(
            name=long_name,
            type="string",
            required=True,
        )
        assert param.name == long_name

    def test_name_with_special_chars(self) -> None:
        """Test name with special characters."""
        param = ModelActionConfigParameter(
            name="my_param-name.v2",
            type="string",
            required=True,
        )
        assert param.name == "my_param-name.v2"

    def test_name_with_unicode(self) -> None:
        """Test name with unicode characters."""
        param = ModelActionConfigParameter(
            name="param_name",
            type="string",
            required=True,
        )
        assert param.name == "param_name"

    def test_default_empty_string(self) -> None:
        """Test default value as empty string."""
        param = ModelActionConfigParameter(
            name="test",
            type="string",
            required=False,
            default="",
        )
        assert param.default == ""

    def test_default_zero_int(self) -> None:
        """Test default value as zero."""
        param = ModelActionConfigParameter(
            name="test",
            type="int",
            required=False,
            default=0,
        )
        assert param.default == 0

    def test_default_zero_float(self) -> None:
        """Test default value as zero float."""
        param = ModelActionConfigParameter(
            name="test",
            type="float",
            required=False,
            default=0.0,
        )
        assert param.default == 0.0

    def test_default_false_bool(self) -> None:
        """Test default value as False."""
        param = ModelActionConfigParameter(
            name="test",
            type="bool",
            required=False,
            default=False,
        )
        assert param.default is False

    def test_default_empty_list(self) -> None:
        """Test default value as empty list."""
        param = ModelActionConfigParameter(
            name="test",
            type="list",
            required=False,
            default=[],
        )
        assert param.default == []

    def test_default_empty_dict(self) -> None:
        """Test default value as empty dict."""
        param = ModelActionConfigParameter(
            name="test",
            type="dict",
            required=False,
            default={},
        )
        assert param.default == {}

    def test_default_negative_int(self) -> None:
        """Test default value as negative int."""
        param = ModelActionConfigParameter(
            name="test",
            type="int",
            required=False,
            default=-42,
        )
        assert param.default == -42

    def test_default_negative_float(self) -> None:
        """Test default value as negative float."""
        param = ModelActionConfigParameter(
            name="test",
            type="float",
            required=False,
            default=-3.14,
        )
        assert param.default == -3.14

    def test_default_large_int(self) -> None:
        """Test default value as large int."""
        param = ModelActionConfigParameter(
            name="test",
            type="int",
            required=False,
            default=10**100,
        )
        assert param.default == 10**100

    def test_default_nested_list(self) -> None:
        """Test default value as nested list."""
        param = ModelActionConfigParameter(
            name="test",
            type="list",
            required=False,
            default=[[1, 2], [3, 4], [[5]]],
        )
        assert param.default == [[1, 2], [3, 4], [[5]]]

    def test_default_nested_dict(self) -> None:
        """Test default value as nested dict."""
        param = ModelActionConfigParameter(
            name="test",
            type="dict",
            required=False,
            default={"a": {"b": {"c": 1}}},
        )
        assert param.default == {"a": {"b": {"c": 1}}}


# =============================================================================
# SECTION 8: Model Configuration Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionConfigParameterModelConfig:
    """Tests for model configuration settings."""

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored (extra='ignore')."""
        param = ModelActionConfigParameter.model_validate(
            {
                "name": "test",
                "type": "string",
                "required": True,
                "unknown_field": "should_be_ignored",
            }
        )
        assert param.name == "test"
        assert not hasattr(param, "unknown_field")

    def test_validate_assignment_enabled(self) -> None:
        """Test that assignment validation is enabled."""
        param = ModelActionConfigParameter(
            name="test",
            type="string",
            required=True,
        )
        # Changing name to empty should fail
        with pytest.raises(ValidationError):
            param.name = ""

    def test_enum_values_not_converted(self) -> None:
        """Test that use_enum_values=False keeps type as string."""
        param = ModelActionConfigParameter(
            name="test",
            type="string",
            required=True,
        )
        # type should remain as the literal string value
        assert param.type == "string"
        assert isinstance(param.type, str)


# =============================================================================
# SECTION 9: Export and Import Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionConfigParameterExports:
    """Tests for module exports."""

    def test_import_from_contracts_package(self) -> None:
        """Test that model can be imported from contracts package."""
        from omnibase_core.models.contracts import ModelActionConfigParameter

        param = ModelActionConfigParameter(
            name="test",
            type="string",
            required=True,
        )
        assert param.name == "test"

    def test_import_parameter_type_from_contracts_package(self) -> None:
        """Test that ParameterType can be imported from contracts package."""
        from omnibase_core.models.contracts import ParameterType

        # ParameterType should be a type alias for Literal
        assert ParameterType is not None

    def test_model_in_all_exports(self) -> None:
        """Test that ModelActionConfigParameter is in __all__."""
        from omnibase_core.models.contracts import __all__

        assert "ModelActionConfigParameter" in __all__

    def test_parameter_type_in_all_exports(self) -> None:
        """Test that ParameterType is in __all__."""
        from omnibase_core.models.contracts import __all__

        assert "ParameterType" in __all__


# =============================================================================
# SECTION 10: Error Message Quality Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionConfigParameterErrorMessages:
    """Tests for error message quality and content."""

    def test_type_mismatch_error_includes_parameter_name(self) -> None:
        """Test that type mismatch error includes parameter name."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="my_special_param",
                type="int",
                required=False,
                default="not_an_int",
            )
        error_message = str(exc_info.value)
        assert "my_special_param" in error_message

    def test_type_mismatch_error_includes_expected_type(self) -> None:
        """Test that type mismatch error includes expected type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="int",
                required=False,
                default="not_an_int",
            )
        error_message = str(exc_info.value)
        assert "int" in error_message.lower()

    def test_type_mismatch_error_includes_actual_type(self) -> None:
        """Test that type mismatch error includes actual type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test",
                type="int",
                required=False,
                default="string_value",
            )
        error_message = str(exc_info.value)
        assert "str" in error_message.lower()

    def test_bool_int_mismatch_error_is_clear(self) -> None:
        """Test that bool/int mismatch error is clear about the issue."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="count",
                type="int",
                required=False,
                default=True,
            )
        error_message = str(exc_info.value)
        assert "bool" in error_message.lower()
        # Error should indicate the declared type was int
        assert "int" in error_message.lower()
