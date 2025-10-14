"""
Test suite for ModelYamlOption - YAML option value with discriminated union.

This test suite focuses on validator branches and factory methods to maximize branch coverage.
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_yaml_option_type import EnumYamlOptionType
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.utils.model_yaml_option import ModelYamlOption


class TestModelYamlOptionInstantiation:
    """Test basic model instantiation."""

    def test_create_boolean_option(self):
        """Test creating boolean option directly."""
        option = ModelYamlOption(
            option_type=EnumYamlOptionType.BOOLEAN, boolean_value=True
        )
        assert option.option_type == EnumYamlOptionType.BOOLEAN
        assert option.boolean_value is True
        assert option.integer_value is None
        assert option.string_value is None

    def test_create_integer_option(self):
        """Test creating integer option directly."""
        option = ModelYamlOption(
            option_type=EnumYamlOptionType.INTEGER, integer_value=42
        )
        assert option.option_type == EnumYamlOptionType.INTEGER
        assert option.integer_value == 42
        assert option.boolean_value is None
        assert option.string_value is None

    def test_create_string_option(self):
        """Test creating string option directly."""
        option = ModelYamlOption(
            option_type=EnumYamlOptionType.STRING, string_value="test"
        )
        assert option.option_type == EnumYamlOptionType.STRING
        assert option.string_value == "test"
        assert option.boolean_value is None
        assert option.integer_value is None


class TestModelYamlOptionFactoryMethods:
    """Test factory methods for creating options."""

    def test_from_bool_true(self):
        """Test from_bool factory with True."""
        option = ModelYamlOption.from_bool(True)
        assert option.option_type == EnumYamlOptionType.BOOLEAN
        assert option.boolean_value is True
        assert option.integer_value is None
        assert option.string_value is None

    def test_from_bool_false(self):
        """Test from_bool factory with False."""
        option = ModelYamlOption.from_bool(False)
        assert option.option_type == EnumYamlOptionType.BOOLEAN
        assert option.boolean_value is False

    def test_from_int_positive(self):
        """Test from_int factory with positive integer."""
        option = ModelYamlOption.from_int(100)
        assert option.option_type == EnumYamlOptionType.INTEGER
        assert option.integer_value == 100
        assert option.boolean_value is None
        assert option.string_value is None

    def test_from_int_zero(self):
        """Test from_int factory with zero."""
        option = ModelYamlOption.from_int(0)
        assert option.option_type == EnumYamlOptionType.INTEGER
        assert option.integer_value == 0

    def test_from_int_negative(self):
        """Test from_int factory with negative integer."""
        option = ModelYamlOption.from_int(-50)
        assert option.option_type == EnumYamlOptionType.INTEGER
        assert option.integer_value == -50

    def test_from_str_normal(self):
        """Test from_str factory with normal string."""
        option = ModelYamlOption.from_str("test_value")
        assert option.option_type == EnumYamlOptionType.STRING
        assert option.string_value == "test_value"
        assert option.boolean_value is None
        assert option.integer_value is None

    def test_from_str_empty(self):
        """Test from_str factory with empty string."""
        option = ModelYamlOption.from_str("")
        assert option.option_type == EnumYamlOptionType.STRING
        assert option.string_value == ""


class TestModelYamlOptionToValueBranches:
    """Test to_value method branches for different types."""

    def test_to_value_boolean_true(self):
        """Test to_value with BOOLEAN type returns boolean (branch: option_type == BOOLEAN)."""
        option = ModelYamlOption.from_bool(True)
        value = option.to_value()
        assert value is True
        assert isinstance(value, bool)

    def test_to_value_boolean_false(self):
        """Test to_value with BOOLEAN type returns False (branch: option_type == BOOLEAN)."""
        option = ModelYamlOption.from_bool(False)
        value = option.to_value()
        assert value is False

    def test_to_value_integer(self):
        """Test to_value with INTEGER type returns integer (branch: option_type == INTEGER)."""
        option = ModelYamlOption.from_int(42)
        value = option.to_value()
        assert value == 42
        assert isinstance(value, int)

    def test_to_value_integer_zero(self):
        """Test to_value with INTEGER type returns zero (branch: option_type == INTEGER)."""
        option = ModelYamlOption.from_int(0)
        value = option.to_value()
        assert value == 0

    def test_to_value_string(self):
        """Test to_value with STRING type returns string (branch: option_type == STRING)."""
        option = ModelYamlOption.from_str("test")
        value = option.to_value()
        assert value == "test"
        assert isinstance(value, str)

    def test_to_value_invalid_type_raises_error(self):
        """Test to_value with invalid type raises error (else branch, line 74)."""
        # Create option with invalid enum value by bypassing validation
        option = ModelYamlOption(
            option_type=EnumYamlOptionType.BOOLEAN, boolean_value=True
        )
        # Manually change to invalid type (simulating corruption)
        # Use object.__setattr__ to bypass Pydantic validate_assignment
        object.__setattr__(option, "option_type", "INVALID_TYPE")

        with pytest.raises(ModelOnexError) as exc_info:
            option.to_value()

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid option_type" in exc_info.value.message


class TestModelYamlOptionProtocolMethods:
    """Test protocol method implementations."""

    def test_serialize_boolean(self):
        """Test serialize protocol method with boolean option."""
        option = ModelYamlOption.from_bool(True)
        serialized = option.serialize()
        assert isinstance(serialized, dict)
        assert serialized["option_type"] == EnumYamlOptionType.BOOLEAN
        assert serialized["boolean_value"] is True

    def test_serialize_integer(self):
        """Test serialize protocol method with integer option."""
        option = ModelYamlOption.from_int(42)
        serialized = option.serialize()
        assert serialized["option_type"] == EnumYamlOptionType.INTEGER
        assert serialized["integer_value"] == 42

    def test_serialize_string(self):
        """Test serialize protocol method with string option."""
        option = ModelYamlOption.from_str("test")
        serialized = option.serialize()
        assert serialized["option_type"] == EnumYamlOptionType.STRING
        assert serialized["string_value"] == "test"

    def test_validate_instance(self):
        """Test validate_instance protocol method."""
        option = ModelYamlOption.from_bool(True)
        assert option.validate_instance() is True


class TestModelYamlOptionEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_model_dump_boolean(self):
        """Test Pydantic model_dump with boolean option."""
        option = ModelYamlOption.from_bool(False)
        dumped = option.model_dump()
        assert dumped["option_type"] == EnumYamlOptionType.BOOLEAN
        assert dumped["boolean_value"] is False
        assert dumped["integer_value"] is None
        assert dumped["string_value"] is None

    def test_model_dump_integer(self):
        """Test Pydantic model_dump with integer option."""
        option = ModelYamlOption.from_int(-100)
        dumped = option.model_dump()
        assert dumped["integer_value"] == -100

    def test_model_dump_string(self):
        """Test Pydantic model_dump with string option."""
        option = ModelYamlOption.from_str("")
        dumped = option.model_dump()
        assert dumped["string_value"] == ""

    def test_round_trip_boolean(self):
        """Test round-trip serialization/deserialization with boolean."""
        original = ModelYamlOption.from_bool(True)
        dumped = original.model_dump()
        restored = ModelYamlOption(**dumped)
        assert restored.option_type == original.option_type
        assert restored.boolean_value == original.boolean_value
        assert restored.to_value() == original.to_value()

    def test_round_trip_integer(self):
        """Test round-trip serialization/deserialization with integer."""
        original = ModelYamlOption.from_int(42)
        dumped = original.model_dump()
        restored = ModelYamlOption(**dumped)
        assert restored.to_value() == 42

    def test_round_trip_string(self):
        """Test round-trip serialization/deserialization with string."""
        original = ModelYamlOption.from_str("test")
        dumped = original.model_dump()
        restored = ModelYamlOption(**dumped)
        assert restored.to_value() == "test"

    def test_all_factory_methods_set_correct_fields(self):
        """Test all factory methods set exactly the right fields."""
        bool_option = ModelYamlOption.from_bool(True)
        assert bool_option.boolean_value is not None
        assert bool_option.integer_value is None
        assert bool_option.string_value is None

        int_option = ModelYamlOption.from_int(10)
        assert int_option.boolean_value is None
        assert int_option.integer_value is not None
        assert int_option.string_value is None

        str_option = ModelYamlOption.from_str("x")
        assert str_option.boolean_value is None
        assert str_option.integer_value is None
        assert str_option.string_value is not None

    def test_large_integer_value(self):
        """Test with large integer values."""
        option = ModelYamlOption.from_int(999999999)
        assert option.to_value() == 999999999

    def test_special_string_values(self):
        """Test with special string values."""
        special_strings = [
            "",
            " ",
            "  spaces  ",
            "newline\n",
            "tab\t",
            "unicode-πάθος",
        ]
        for s in special_strings:
            option = ModelYamlOption.from_str(s)
            assert option.to_value() == s
