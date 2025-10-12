"""
Test suite for ModelValidationValue - validation value object with discriminated union pattern.

This test suite focuses on validator branches and edge cases to maximize branch coverage.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_validation_value_type import EnumValidationValueType
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_validation_value import ModelValidationValue


class TestModelValidationValueInstantiation:
    """Test basic model instantiation and validators."""

    def test_create_string_value_valid(self):
        """Test creating string validation value with valid data."""
        value = ModelValidationValue(
            value_type=EnumValidationValueType.STRING,
            raw_value="test_string"
        )
        assert value.value_type == EnumValidationValueType.STRING
        assert value.raw_value == "test_string"

    def test_create_integer_value_valid(self):
        """Test creating integer validation value with valid data."""
        value = ModelValidationValue(
            value_type=EnumValidationValueType.INTEGER,
            raw_value=42
        )
        assert value.value_type == EnumValidationValueType.INTEGER
        assert value.raw_value == 42

    def test_create_boolean_value_valid(self):
        """Test creating boolean validation value with valid data."""
        value = ModelValidationValue(
            value_type=EnumValidationValueType.BOOLEAN,
            raw_value=True
        )
        assert value.value_type == EnumValidationValueType.BOOLEAN
        assert value.raw_value is True

    def test_create_null_value_valid(self):
        """Test creating null validation value with None."""
        value = ModelValidationValue(
            value_type=EnumValidationValueType.NULL,
            raw_value=None
        )
        assert value.value_type == EnumValidationValueType.NULL
        assert value.raw_value is None


class TestModelValidationValueValidatorBranches:
    """Test validator branches for raw_value field validation."""

    def test_string_value_with_wrong_type_raises_error(self):
        """Test STRING type with non-string value raises error (validator branch)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidationValue(
                value_type=EnumValidationValueType.STRING,
                raw_value=123  # Wrong type
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "String validation value must contain str data" in str(exc_info.value)

    def test_integer_value_with_wrong_type_raises_error(self):
        """Test INTEGER type with non-integer value raises error (validator branch)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidationValue(
                value_type=EnumValidationValueType.INTEGER,
                raw_value="not_an_int"  # Wrong type
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Integer validation value must contain int data" in str(exc_info.value)

    def test_boolean_value_with_wrong_type_raises_error(self):
        """Test BOOLEAN type with non-boolean value raises error (validator branch)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidationValue(
                value_type=EnumValidationValueType.BOOLEAN,
                raw_value="true"  # Wrong type (string, not bool)
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Boolean validation value must contain bool data" in str(exc_info.value)

    def test_null_value_with_non_none_raises_error(self):
        """Test NULL type with non-None value raises error (validator branch)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidationValue(
                value_type=EnumValidationValueType.NULL,
                raw_value="not_none"  # Wrong value
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Null validation value must contain None" in str(exc_info.value)

    def test_boolean_integer_not_confused(self):
        """Test that boolean False (which is also 0) is not accepted as integer."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidationValue(
                value_type=EnumValidationValueType.INTEGER,
                raw_value=False  # bool is subclass of int in Python
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


class TestModelValidationValueFactoryMethods:
    """Test factory methods for creating validation values."""

    def test_from_string_factory(self):
        """Test from_string factory method."""
        value = ModelValidationValue.from_string("test")
        assert value.value_type == EnumValidationValueType.STRING
        assert value.raw_value == "test"

    def test_from_integer_factory(self):
        """Test from_integer factory method."""
        value = ModelValidationValue.from_integer(100)
        assert value.value_type == EnumValidationValueType.INTEGER
        assert value.raw_value == 100

    def test_from_boolean_factory(self):
        """Test from_boolean factory method."""
        value = ModelValidationValue.from_boolean(False)
        assert value.value_type == EnumValidationValueType.BOOLEAN
        assert value.raw_value is False

    def test_from_null_factory(self):
        """Test from_null factory method."""
        value = ModelValidationValue.from_null()
        assert value.value_type == EnumValidationValueType.NULL
        assert value.raw_value is None


class TestModelValidationValueFromAnyBranches:
    """Test from_any method branches for automatic type detection."""

    def test_from_any_with_none_creates_null(self):
        """Test from_any with None creates NULL type (branch: value is None)."""
        value = ModelValidationValue.from_any(None)
        assert value.value_type == EnumValidationValueType.NULL
        assert value.raw_value is None

    def test_from_any_with_string_creates_string(self):
        """Test from_any with string creates STRING type (branch: isinstance(value, str))."""
        value = ModelValidationValue.from_any("hello")
        assert value.value_type == EnumValidationValueType.STRING
        assert value.raw_value == "hello"

    def test_from_any_with_boolean_creates_boolean(self):
        """Test from_any with bool creates BOOLEAN type (branch: isinstance(value, bool)).

        NOTE: Must check bool before int because bool is subclass of int in Python.
        """
        value = ModelValidationValue.from_any(True)
        assert value.value_type == EnumValidationValueType.BOOLEAN
        assert value.raw_value is True

    def test_from_any_with_integer_creates_integer(self):
        """Test from_any with int creates INTEGER type (branch: isinstance(value, int))."""
        value = ModelValidationValue.from_any(42)
        assert value.value_type == EnumValidationValueType.INTEGER
        assert value.raw_value == 42

    def test_from_any_with_unknown_type_converts_to_string(self):
        """Test from_any with unknown type converts to string (fallback branch)."""
        class CustomClass:
            def __str__(self):
                return "custom_value"

        custom_obj = CustomClass()
        value = ModelValidationValue.from_any(custom_obj)
        assert value.value_type == EnumValidationValueType.STRING
        assert value.raw_value == "custom_value"

    def test_from_any_with_list_converts_to_string(self):
        """Test from_any with list converts to string (fallback branch)."""
        value = ModelValidationValue.from_any([1, 2, 3])
        assert value.value_type == EnumValidationValueType.STRING
        assert value.raw_value == "[1, 2, 3]"

    def test_from_any_with_dict_converts_to_string(self):
        """Test from_any with dict converts to string (fallback branch)."""
        value = ModelValidationValue.from_any({"key": "value"})
        assert value.value_type == EnumValidationValueType.STRING
        assert value.raw_value == "{'key': 'value'}"

    def test_from_any_with_float_converts_to_string(self):
        """Test from_any with float converts to string (fallback branch)."""
        value = ModelValidationValue.from_any(3.14)
        assert value.value_type == EnumValidationValueType.STRING
        assert value.raw_value == "3.14"


class TestModelValidationValueConversion:
    """Test conversion methods."""

    def test_to_python_value_string(self):
        """Test converting string value back to Python value."""
        value = ModelValidationValue.from_string("test")
        assert value.to_python_value() == "test"

    def test_to_python_value_integer(self):
        """Test converting integer value back to Python value."""
        value = ModelValidationValue.from_integer(42)
        assert value.to_python_value() == 42

    def test_to_python_value_boolean(self):
        """Test converting boolean value back to Python value."""
        value = ModelValidationValue.from_boolean(True)
        assert value.to_python_value() is True

    def test_to_python_value_null(self):
        """Test converting null value back to Python value."""
        value = ModelValidationValue.from_null()
        assert value.to_python_value() is None


class TestModelValidationValueStrMethod:
    """Test __str__ method branches."""

    def test_str_with_null_type_returns_null(self):
        """Test __str__ with NULL type returns 'null' (branch: value_type == NULL)."""
        value = ModelValidationValue.from_null()
        assert str(value) == "null"

    def test_str_with_string_type_returns_value(self):
        """Test __str__ with STRING type returns string value (else branch)."""
        value = ModelValidationValue.from_string("test")
        assert str(value) == "test"

    def test_str_with_integer_type_returns_value(self):
        """Test __str__ with INTEGER type returns string of value (else branch)."""
        value = ModelValidationValue.from_integer(42)
        assert str(value) == "42"

    def test_str_with_boolean_type_returns_value(self):
        """Test __str__ with BOOLEAN type returns string of value (else branch)."""
        value = ModelValidationValue.from_boolean(True)
        assert str(value) == "True"


class TestModelValidationValueProtocolMethods:
    """Test protocol method implementations."""

    def test_validate_instance_returns_true(self):
        """Test validate_instance protocol method."""
        value = ModelValidationValue.from_string("test")
        assert value.validate_instance() is True

    def test_serialize_returns_dict(self):
        """Test serialize protocol method."""
        value = ModelValidationValue.from_string("test")
        serialized = value.serialize()
        assert isinstance(serialized, dict)
        assert "value_type" in serialized
        assert "raw_value" in serialized


class TestModelValidationValueEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string_valid(self):
        """Test empty string is valid for STRING type."""
        value = ModelValidationValue.from_string("")
        assert value.value_type == EnumValidationValueType.STRING
        assert value.raw_value == ""

    def test_zero_integer_valid(self):
        """Test zero is valid for INTEGER type."""
        value = ModelValidationValue.from_integer(0)
        assert value.value_type == EnumValidationValueType.INTEGER
        assert value.raw_value == 0

    def test_negative_integer_valid(self):
        """Test negative integer is valid for INTEGER type."""
        value = ModelValidationValue.from_integer(-100)
        assert value.value_type == EnumValidationValueType.INTEGER
        assert value.raw_value == -100

    def test_false_boolean_valid(self):
        """Test False is valid for BOOLEAN type."""
        value = ModelValidationValue.from_boolean(False)
        assert value.value_type == EnumValidationValueType.BOOLEAN
        assert value.raw_value is False

    def test_model_dump_serialization(self):
        """Test Pydantic model_dump serialization."""
        value = ModelValidationValue.from_string("test")
        dumped = value.model_dump()
        assert dumped["value_type"] == EnumValidationValueType.STRING
        assert dumped["raw_value"] == "test"

    def test_round_trip_serialization(self):
        """Test round-trip serialization/deserialization."""
        original = ModelValidationValue.from_integer(42)
        dumped = original.model_dump()
        restored = ModelValidationValue(**dumped)
        assert restored.value_type == original.value_type
        assert restored.raw_value == original.raw_value
