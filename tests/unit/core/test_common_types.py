"""
Tests for common types used across ONEX core modules.

Tests the Pydantic models and validation logic to ensure proper type safety.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.core.common_types import ModelScalarValue, ModelStateValue


class TestModelScalarValue:
    """Test cases for ModelScalarValue."""

    def test_create_string_scalar(self):
        """Test creating a string scalar value."""
        scalar = ModelScalarValue.create_string("test")
        assert scalar.value == "test"
        assert scalar.type_hint == "str"

    def test_create_int_scalar(self):
        """Test creating an integer scalar value."""
        scalar = ModelScalarValue.create_int(42)
        assert scalar.value == 42
        assert scalar.type_hint == "int"

    def test_create_float_scalar(self):
        """Test creating a float scalar value."""
        scalar = ModelScalarValue.create_float(3.14)
        assert scalar.value == 3.14
        assert scalar.type_hint == "float"

    def test_create_bool_scalar(self):
        """Test creating a boolean scalar value."""
        scalar = ModelScalarValue.create_bool(True)
        assert scalar.value is True
        assert scalar.type_hint == "bool"

    def test_from_primitive(self):
        """Test creating scalar from primitive value."""
        scalar = ModelScalarValue.from_primitive("test")
        assert scalar.value == "test"
        assert scalar.type_hint == "str"

    def test_to_primitive(self):
        """Test extracting primitive value."""
        scalar = ModelScalarValue(value=123)
        assert scalar.to_primitive() == 123

    def test_type_hint_auto_generation(self):
        """Test that type_hint property is auto-generated correctly."""
        assert ModelScalarValue(value="str").type_hint == "str"
        assert ModelScalarValue(value=123).type_hint == "int"
        assert ModelScalarValue(value=1.23).type_hint == "float"
        assert ModelScalarValue(value=True).type_hint == "bool"


class TestModelStateValue:
    """Test cases for ModelStateValue."""

    def test_create_scalar_value(self):
        """Test creating state value from scalar."""
        state = ModelStateValue.create_scalar("test")
        assert state.scalar_value == "test"
        assert state.dict_value is None
        assert state.is_null is False
        assert state.get_value() == "test"

    def test_create_dict_value(self):
        """Test creating state value from dictionary."""
        test_dict = {"key": "value"}
        state = ModelStateValue.create_dict(test_dict)
        assert state.scalar_value is None
        assert state.dict_value == test_dict
        assert state.is_null is False
        assert state.get_value() == test_dict

    def test_create_null_value(self):
        """Test creating null state value."""
        state = ModelStateValue.create_null()
        assert state.scalar_value is None
        assert state.dict_value is None
        assert state.is_null is True
        assert state.get_value() is None

    def test_validation_prevents_multiple_values(self):
        """Test that validation prevents setting multiple values."""
        # This should fail validation
        with pytest.raises(ValidationError) as exc_info:
            ModelStateValue(
                scalar_value="test", dict_value={"key": "value"}, is_null=False
            )

        error_message = str(exc_info.value)
        assert "can only have one of" in error_message

    def test_validation_allows_single_scalar(self):
        """Test that validation allows single scalar value."""
        state = ModelStateValue(scalar_value="test")
        assert state.scalar_value == "test"
        assert state.dict_value is None
        assert state.is_null is False

    def test_validation_allows_single_dict(self):
        """Test that validation allows single dict value."""
        test_dict = {"key": "value"}
        state = ModelStateValue(dict_value=test_dict)
        assert state.scalar_value is None
        assert state.dict_value == test_dict
        assert state.is_null is False

    def test_validation_allows_null_only(self):
        """Test that validation allows null value only."""
        state = ModelStateValue(is_null=True)
        assert state.scalar_value is None
        assert state.dict_value is None
        assert state.is_null is True

    def test_validation_prevents_scalar_and_null(self):
        """Test that validation prevents scalar value with null flag."""
        with pytest.raises(ValidationError) as exc_info:
            ModelStateValue(scalar_value="test", is_null=True)

        error_message = str(exc_info.value)
        assert "can only have one of" in error_message

    def test_validation_prevents_dict_and_null(self):
        """Test that validation prevents dict value with null flag."""
        with pytest.raises(ValidationError) as exc_info:
            ModelStateValue(dict_value={"key": "value"}, is_null=True)

        error_message = str(exc_info.value)
        assert "can only have one of" in error_message

    def test_get_value_returns_correct_type(self):
        """Test get_value returns the correct value based on what's set."""
        # Scalar value
        scalar_state = ModelStateValue(scalar_value=42)
        assert scalar_state.get_value() == 42

        # Dict value
        test_dict = {"key": "value"}
        dict_state = ModelStateValue(dict_value=test_dict)
        assert dict_state.get_value() == test_dict

        # Null value
        null_state = ModelStateValue(is_null=True)
        assert null_state.get_value() is None

        # Empty state (should return None)
        empty_state = ModelStateValue()
        assert empty_state.get_value() is None
