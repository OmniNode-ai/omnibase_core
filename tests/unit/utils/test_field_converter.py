"""Tests for field converter utility."""

import pytest

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_field_converter import FieldConverter


class TestFieldConverter:
    """Test FieldConverter functionality."""

    def test_field_converter_basic_conversion(self):
        """Test basic field conversion."""
        converter = FieldConverter(
            field_name="test_field", converter=int, default_value=None
        )

        result = converter.convert("42")
        assert result == 42

    def test_field_converter_with_default_value(self):
        """Test field converter with default value."""
        converter = FieldConverter(
            field_name="test_field", converter=int, default_value=0
        )

        # Test successful conversion
        result = converter.convert("42")
        assert result == 42

        # Test fallback to default on error
        result = converter.convert("invalid")
        assert result == 0

    def test_field_converter_with_validator(self):
        """Test field converter with validator."""

        def positive_validator(value: int) -> bool:
            return value > 0

        converter = FieldConverter(
            field_name="test_field", converter=int, validator=positive_validator
        )

        # Test valid conversion
        result = converter.convert("42")
        assert result == 42

        # Test invalid conversion (should raise error)
        with pytest.raises(ModelOnexError):
            converter.convert("-1")

    def test_field_converter_string_conversion(self):
        """Test string field conversion."""
        converter = FieldConverter(
            field_name="string_field", converter=str, default_value="default"
        )

        result = converter.convert("test")
        assert result == "test"

    def test_field_converter_float_conversion(self):
        """Test float field conversion."""
        converter = FieldConverter(
            field_name="float_field", converter=float, default_value=0.0
        )

        result = converter.convert("3.14")
        assert result == 3.14

    def test_field_converter_boolean_conversion(self):
        """Test boolean field conversion."""
        converter = FieldConverter(
            field_name="bool_field",
            converter=lambda x: x.lower() == "true",
            default_value=False,
        )

        result = converter.convert("true")
        assert result is True

        result = converter.convert("false")
        assert result is False

    def test_field_converter_custom_converter(self):
        """Test field converter with custom converter function."""

        def custom_converter(value: str) -> str:
            return value.upper()

        converter = FieldConverter(
            field_name="custom_field",
            converter=custom_converter,
            default_value="DEFAULT",
        )

        result = converter.convert("hello")
        assert result == "HELLO"

    def test_field_converter_conversion_error(self):
        """Test field converter with conversion error."""
        converter = FieldConverter(
            field_name="int_field", converter=int, default_value=None
        )

        # Should raise ModelOnexError when conversion fails and no default
        with pytest.raises(ModelOnexError) as exc_info:
            converter.convert("not_a_number")

        assert "Failed to convert field int_field" in str(exc_info.value)

    def test_field_converter_validator_failure(self):
        """Test field converter with validator failure."""

        def even_validator(value: int) -> bool:
            return value % 2 == 0

        converter = FieldConverter(
            field_name="even_field", converter=int, validator=even_validator
        )

        # Should raise ModelOnexError when validator fails
        with pytest.raises(ModelOnexError) as exc_info:
            converter.convert("3")

        assert "Validation failed for field even_field" in str(exc_info.value)

    def test_field_converter_with_default_on_error(self):
        """Test field converter uses default value on error."""
        converter = FieldConverter(
            field_name="test_field", converter=int, default_value=999
        )

        # Should return default value on conversion error
        result = converter.convert("invalid")
        assert result == 999

    def test_field_converter_no_default_on_error(self):
        """Test field converter raises error when no default value."""
        converter = FieldConverter(
            field_name="test_field", converter=int, default_value=None
        )

        # Should raise error when no default value
        with pytest.raises(ModelOnexError):
            converter.convert("invalid")

    def test_field_converter_frozen_dataclass(self):
        """Test that FieldConverter is frozen (immutable)."""
        converter = FieldConverter(
            field_name="test_field", converter=int, default_value=0
        )

        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            converter.field_name = "new_field"

    def test_field_converter_complex_validator(self):
        """Test field converter with complex validator."""

        def range_validator(value: int) -> bool:
            return 0 <= value <= 100

        converter = FieldConverter(
            field_name="range_field", converter=int, validator=range_validator
        )

        # Test valid range
        result = converter.convert("50")
        assert result == 50

        # Test invalid range (too high)
        with pytest.raises(ModelOnexError):
            converter.convert("150")

        # Test invalid range (too low)
        with pytest.raises(ModelOnexError):
            converter.convert("-10")

    def test_field_converter_none_validator(self):
        """Test field converter with None validator (should not validate)."""
        converter = FieldConverter(
            field_name="test_field", converter=int, validator=None
        )

        # Should work without validation
        result = converter.convert("42")
        assert result == 42

    def test_field_converter_error_context(self):
        """Test that error includes proper context."""
        converter = FieldConverter(
            field_name="test_field", converter=int, default_value=None
        )

        with pytest.raises(ModelOnexError) as exc_info:
            converter.convert("invalid")

        error = exc_info.value
        assert error.error_code is not None
        assert "test_field" in str(error.message)
        # ModelOnexError exposes structured context via .context
        assert isinstance(error.context, dict)

    def test_field_converter_validator_error_context(self):
        """Test that validator error includes proper context."""

        def failing_validator(value: int) -> bool:
            return False

        converter = FieldConverter(
            field_name="test_field", converter=int, validator=failing_validator
        )

        with pytest.raises(ModelOnexError) as exc_info:
            converter.convert("42")

        error = exc_info.value
        assert error.error_code is not None
        assert "Validation failed for field test_field" in str(error.message)
        # ModelOnexError exposes structured context via .context
        assert isinstance(error.context, dict)
