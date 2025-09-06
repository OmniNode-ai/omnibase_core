"""
Tests for common types used across ONEX core modules.

Tests the Pydantic models and validation logic to ensure proper type safety.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.core.common_types import (
    ModelConfiguration,
    ModelMetadata,
    ModelScalarValue,
    ModelStateValue,
)


class TestModelScalarValue:
    """Test cases for ModelScalarValue."""

    def test_create_string_scalar(self):
        """Test creating a string scalar value."""
        scalar = ModelScalarValue.create_string("test")
        assert scalar.string_value == "test"
        assert scalar.type_hint == "str"

    def test_create_int_scalar(self):
        """Test creating an integer scalar value."""
        scalar = ModelScalarValue.create_int(42)
        assert scalar.int_value == 42
        assert scalar.type_hint == "int"

    def test_create_float_scalar(self):
        """Test creating a float scalar value."""
        scalar = ModelScalarValue.create_float(3.14)
        assert scalar.float_value == 3.14
        assert scalar.type_hint == "float"

    def test_create_bool_scalar(self):
        """Test creating a boolean scalar value."""
        scalar = ModelScalarValue.create_bool(True)
        assert scalar.bool_value is True
        assert scalar.type_hint == "bool"

    def test_from_string_primitive(self):
        """Test creating scalar from string primitive value."""
        scalar = ModelScalarValue.from_string_primitive("test")
        assert scalar.string_value == "test"
        assert scalar.type_hint == "str"

    def test_from_int_primitive(self):
        """Test creating scalar from int primitive value."""
        scalar = ModelScalarValue.from_int_primitive(123)
        assert scalar.int_value == 123
        assert scalar.type_hint == "int"

    def test_to_string_primitive(self):
        """Test extracting string primitive value."""
        scalar = ModelScalarValue.create_string("test")
        assert scalar.to_string_primitive() == "test"

    def test_to_int_primitive(self):
        """Test extracting int primitive value."""
        scalar = ModelScalarValue.create_int(123)
        assert scalar.to_int_primitive() == 123

    def test_type_hint_auto_generation(self):
        """Test that type_hint property is auto-generated correctly."""
        assert ModelScalarValue.create_string("str").type_hint == "str"
        assert ModelScalarValue.create_int(123).type_hint == "int"
        assert ModelScalarValue.create_float(1.23).type_hint == "float"
        assert ModelScalarValue.create_bool(True).type_hint == "bool"

    def test_validation_requires_exactly_one_value(self):
        """Test that validation requires exactly one value to be set."""
        # No values set should fail
        with pytest.raises(ValidationError):
            ModelScalarValue()

        # Multiple values set should fail
        with pytest.raises(ValidationError):
            ModelScalarValue(string_value="test", int_value=42)

    def test_validation_constraints_security(self):
        """Test that validation constraints prevent security issues."""
        # Test string length constraint
        with pytest.raises(ValidationError):
            ModelScalarValue.create_string("x" * 65537)  # Exceeds max_length

        # Test integer range constraints
        with pytest.raises(ValidationError):
            ModelScalarValue.create_int(2**63)  # Exceeds max value

        with pytest.raises(ValidationError):
            ModelScalarValue.create_int(-(2**63) - 1)  # Below min value

        # Valid values should work
        valid_string = ModelScalarValue.create_string("x" * 65536)  # At limit
        assert valid_string.string_value == "x" * 65536

        valid_int = ModelScalarValue.create_int(2**63 - 1)  # At max
        assert valid_int.int_value == 2**63 - 1


class TestModelStateValue:
    """Test cases for ModelStateValue."""

    def test_create_scalar_string_value(self):
        """Test creating state value from string scalar."""
        state = ModelStateValue.create_scalar_string("test")
        assert state.scalar_value is not None
        assert state.scalar_value.string_value == "test"
        scalar_value = state.get_scalar_value()
        assert scalar_value is not None
        assert scalar_value.to_string_primitive() == "test"

    def test_create_scalar_int_value(self):
        """Test creating state value from int scalar."""
        state = ModelStateValue.create_scalar_int(42)
        assert state.scalar_value is not None
        assert state.scalar_value.int_value == 42
        scalar_value = state.get_scalar_value()
        assert scalar_value is not None
        assert scalar_value.to_int_primitive() == 42

    def test_create_metadata_value(self):
        """Test creating state value from metadata."""
        entries = {
            "key1": ModelScalarValue.create_string("value1"),
            "key2": ModelScalarValue.create_int(123),
        }
        state = ModelStateValue.create_metadata(entries)
        assert state.metadata_value is not None
        assert state.metadata_value.entries == entries
        assert state.get_metadata_value() == state.metadata_value

    def test_create_config_value(self):
        """Test creating state value from configuration."""
        settings = {
            "setting1": ModelScalarValue.create_bool(True),
            "setting2": ModelScalarValue.create_float(3.14),
        }
        state = ModelStateValue.create_config(settings)
        assert state.config_value is not None
        assert state.config_value.settings == settings
        assert state.get_config_value() == state.config_value

    def test_create_null_value(self):
        """Test creating null state value."""
        state = ModelStateValue.create_null()
        assert state.is_null is True
        assert state.is_null_value() is True
        assert state.get_scalar_value() is None

    def test_validation_prevents_multiple_values(self):
        """Test that validation prevents setting multiple values."""
        scalar_value = ModelScalarValue.create_string("test")
        metadata_value = ModelMetadata(entries={})

        with pytest.raises(ValidationError) as exc_info:
            ModelStateValue(scalar_value=scalar_value, metadata_value=metadata_value)

        error_message = str(exc_info.value)
        assert "can only have one of" in error_message

    def test_validation_allows_single_scalar(self):
        """Test that validation allows single scalar value."""
        scalar_value = ModelScalarValue.create_string("test")
        state = ModelStateValue(scalar_value=scalar_value)
        assert state.scalar_value == scalar_value
        assert state.metadata_value is None
        assert state.is_null is False

    def test_validation_allows_single_metadata(self):
        """Test that validation allows single metadata value."""
        metadata_value = ModelMetadata(entries={})
        state = ModelStateValue(metadata_value=metadata_value)
        assert state.scalar_value is None
        assert state.metadata_value == metadata_value
        assert state.is_null is False

    def test_validation_allows_null_only(self):
        """Test that validation allows null value only."""
        state = ModelStateValue(is_null=True)
        assert state.scalar_value is None
        assert state.metadata_value is None
        assert state.config_value is None
        assert state.is_null is True

    def test_validation_prevents_scalar_and_null(self):
        """Test that validation prevents scalar value with null flag."""
        scalar_value = ModelScalarValue.create_string("test")
        with pytest.raises(ValidationError) as exc_info:
            ModelStateValue(scalar_value=scalar_value, is_null=True)

        error_message = str(exc_info.value)
        assert "can only have one of" in error_message

    def test_empty_state_defaults_to_null(self):
        """Test that empty state defaults to null."""
        state = ModelStateValue()
        assert state.is_null is True
        assert state.is_null_value() is True


class TestModelMetadata:
    """Test cases for ModelMetadata."""

    def test_create_empty_metadata(self):
        """Test creating empty metadata container."""
        metadata = ModelMetadata()
        assert metadata.entries == {}

    def test_create_metadata_with_entries(self):
        """Test creating metadata with entries."""
        entries = {
            "name": ModelScalarValue.create_string("test"),
            "version": ModelScalarValue.create_int(1),
        }
        metadata = ModelMetadata(entries=entries)
        assert metadata.entries == entries


class TestModelConfiguration:
    """Test cases for ModelConfiguration."""

    def test_create_empty_configuration(self):
        """Test creating empty configuration container."""
        config = ModelConfiguration()
        assert config.settings == {}

    def test_create_configuration_with_settings(self):
        """Test creating configuration with settings."""
        settings = {
            "debug": ModelScalarValue.create_bool(True),
            "timeout": ModelScalarValue.create_float(30.5),
        }
        config = ModelConfiguration(settings=settings)
        assert config.settings == settings
