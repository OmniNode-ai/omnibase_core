"""
Comprehensive unit tests for ModelFieldConverterRegistry and FieldConverter.

Tests cover:
- Field converter initialization and registration
- Boolean field conversion with custom true values
- Integer field conversion with validation bounds
- Enum field conversion with value and name matching
- Optional integer field conversion with zero-as-none
- Custom field converters with validators
- Bulk data conversion
- Error handling and validation failures
"""

from __future__ import annotations

from enum import Enum

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.utils.model_field_converter import (
    FieldConverter,
    ModelFieldConverterRegistry,
)


# Test enum for enum field tests
class TestStatus(Enum):
    """Test enum for converter tests."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class TestFieldConverter:
    """Test FieldConverter class."""

    def test_field_converter_initialization(self) -> None:
        """Test FieldConverter initialization."""
        converter = FieldConverter(
            field_name="test_field",
            converter=int,
            default_value=0,
        )
        assert converter.field_name == "test_field"
        assert converter.default_value == 0
        assert converter.validator is None

    def test_field_converter_with_validator(self) -> None:
        """Test FieldConverter with validator."""

        def is_positive(value: int) -> bool:
            return value > 0

        converter = FieldConverter(
            field_name="positive_number",
            converter=int,
            validator=is_positive,
        )
        # Valid positive number
        result = converter.convert("42")
        assert result == 42

        # Invalid negative number
        with pytest.raises(ModelOnexError) as exc_info:
            converter.convert("-5")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Validation failed" in exc_info.value.message

    def test_field_converter_successful_conversion(self) -> None:
        """Test successful field conversion."""
        converter = FieldConverter(
            field_name="age",
            converter=int,
        )
        result = converter.convert("25")
        assert result == 25
        assert isinstance(result, int)

    def test_field_converter_with_default_on_error(self) -> None:
        """Test field converter uses default value on conversion error."""
        converter = FieldConverter(
            field_name="optional_field",
            converter=int,
            default_value=0,
        )
        result = converter.convert("not_a_number")
        assert result == 0

    def test_field_converter_raises_onex_error_without_default(self) -> None:
        """Test field converter raises ModelOnexError when no default provided."""
        converter = FieldConverter(
            field_name="required_field",
            converter=int,
        )
        with pytest.raises(ModelOnexError) as exc_info:
            converter.convert("invalid")
        assert exc_info.value.error_code == EnumCoreErrorCode.CONVERSION_ERROR
        assert "Failed to convert field" in exc_info.value.message

    def test_field_converter_reraises_onex_error(self) -> None:
        """Test field converter re-raises ModelOnexError from converter."""

        def raises_onex_error(value: str) -> int:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Custom error",
            )

        converter = FieldConverter(
            field_name="error_field",
            converter=raises_onex_error,
        )
        with pytest.raises(ModelOnexError) as exc_info:
            converter.convert("anything")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Custom error" in exc_info.value.message


class TestModelFieldConverterRegistry:
    """Test ModelFieldConverterRegistry class."""

    def test_registry_initialization(self) -> None:
        """Test registry initialization."""
        registry = ModelFieldConverterRegistry()
        assert registry.list_fields() == []
        assert not registry.has_converter("any_field")

    def test_register_boolean_field_default_true_values(self) -> None:
        """Test boolean field registration with default true values."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("enabled")

        # Test default true values
        assert registry.convert_field("enabled", "true") is True
        assert registry.convert_field("enabled", "TRUE") is True
        assert registry.convert_field("enabled", "1") is True
        assert registry.convert_field("enabled", "yes") is True
        assert registry.convert_field("enabled", "YES") is True
        assert registry.convert_field("enabled", "on") is True

        # Test false values
        assert registry.convert_field("enabled", "false") is False
        assert registry.convert_field("enabled", "0") is False
        assert registry.convert_field("enabled", "no") is False

    def test_register_boolean_field_custom_true_values(self) -> None:
        """Test boolean field registration with custom true values."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field(
            "custom_bool",
            true_values={"y", "enabled", "active"},
        )

        assert registry.convert_field("custom_bool", "y") is True
        assert registry.convert_field("custom_bool", "enabled") is True
        assert registry.convert_field("custom_bool", "active") is True
        assert registry.convert_field("custom_bool", "n") is False
        assert (
            registry.convert_field("custom_bool", "true") is False
        )  # Not in custom set

    def test_register_boolean_field_with_default(self) -> None:
        """Test boolean field with default value."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("optional_bool", default=False)

        # Should use default for invalid conversion
        result = registry.convert_field("optional_bool", "invalid")
        assert result is False

    def test_register_integer_field_basic(self) -> None:
        """Test basic integer field registration."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("count")

        result = registry.convert_field("count", "42")
        assert result == 42
        assert isinstance(result, int)

    def test_register_integer_field_with_min_value(self) -> None:
        """Test integer field with minimum value validation."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("age", min_value=0)

        # Valid value
        result = registry.convert_field("age", "25")
        assert result == 25

        # Invalid value below minimum
        with pytest.raises(ModelOnexError) as exc_info:
            registry.convert_field("age", "-5")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_register_integer_field_with_max_value(self) -> None:
        """Test integer field with maximum value validation."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("percentage", max_value=100)

        # Valid value
        result = registry.convert_field("percentage", "75")
        assert result == 75

        # Invalid value above maximum
        with pytest.raises(ModelOnexError) as exc_info:
            registry.convert_field("percentage", "150")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_register_integer_field_with_bounds(self) -> None:
        """Test integer field with both min and max bounds."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("score", min_value=0, max_value=100)

        # Valid values
        assert registry.convert_field("score", "0") == 0
        assert registry.convert_field("score", "50") == 50
        assert registry.convert_field("score", "100") == 100

        # Invalid values
        with pytest.raises(ModelOnexError):
            registry.convert_field("score", "-1")
        with pytest.raises(ModelOnexError):
            registry.convert_field("score", "101")

    def test_register_integer_field_with_default(self) -> None:
        """Test integer field with default value."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("optional_count", default=0)

        result = registry.convert_field("optional_count", "not_a_number")
        assert result == 0

    def test_register_enum_field_by_value(self) -> None:
        """Test enum field conversion by value."""
        registry = ModelFieldConverterRegistry()
        registry.register_enum_field("status", TestStatus)

        result = registry.convert_field("status", "active")
        assert result == TestStatus.ACTIVE
        assert isinstance(result, TestStatus)

    def test_register_enum_field_by_name(self) -> None:
        """Test enum field conversion by name (case-insensitive)."""
        registry = ModelFieldConverterRegistry()
        registry.register_enum_field("status", TestStatus)

        # Test case-insensitive name matching
        result = registry.convert_field("status", "ACTIVE")
        assert result == TestStatus.ACTIVE

        result = registry.convert_field("status", "Inactive")
        assert result == TestStatus.INACTIVE

    def test_register_enum_field_invalid_value(self) -> None:
        """Test enum field with invalid value."""
        registry = ModelFieldConverterRegistry()
        registry.register_enum_field("status", TestStatus)

        with pytest.raises(ModelOnexError) as exc_info:
            registry.convert_field("status", "invalid_status")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid TestStatus value" in exc_info.value.message

    def test_register_enum_field_with_default(self) -> None:
        """Test enum field with default value."""
        registry = ModelFieldConverterRegistry()
        registry.register_enum_field("status", TestStatus, default=TestStatus.PENDING)

        result = registry.convert_field("status", "invalid")
        assert result == TestStatus.PENDING

    def test_register_optional_integer_field_empty_string(self) -> None:
        """Test optional integer field with empty string."""
        registry = ModelFieldConverterRegistry()
        registry.register_optional_integer_field("optional_id")

        result = registry.convert_field("optional_id", "")
        assert result is None

    def test_register_optional_integer_field_zero_as_none(self) -> None:
        """Test optional integer field with zero treated as None."""
        registry = ModelFieldConverterRegistry()
        registry.register_optional_integer_field("optional_count", zero_as_none=True)

        assert registry.convert_field("optional_count", "0") is None
        assert registry.convert_field("optional_count", "5") == 5

    def test_register_optional_integer_field_zero_as_value(self) -> None:
        """Test optional integer field with zero as valid value."""
        registry = ModelFieldConverterRegistry()
        registry.register_optional_integer_field("count", zero_as_none=False)

        assert registry.convert_field("count", "0") == 0
        assert registry.convert_field("count", "") is None

    def test_register_custom_field_basic(self) -> None:
        """Test custom field converter registration."""

        def parse_csv(value: str) -> list[str]:
            return [item.strip() for item in value.split(",")]

        registry = ModelFieldConverterRegistry()
        registry.register_custom_field("tags", parse_csv)

        result = registry.convert_field("tags", "python, testing, onex")
        assert result == ["python", "testing", "onex"]

    def test_register_custom_field_with_validator(self) -> None:
        """Test custom field with validator."""

        def parse_int(value: str) -> int:
            return int(value)

        def is_even(value: object) -> bool:
            return isinstance(value, int) and value % 2 == 0

        registry = ModelFieldConverterRegistry()
        registry.register_custom_field(
            "even_number",
            parse_int,
            validator=is_even,
        )

        # Valid even number
        assert registry.convert_field("even_number", "42") == 42

        # Invalid odd number
        with pytest.raises(ModelOnexError) as exc_info:
            registry.convert_field("even_number", "43")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_register_custom_field_with_default(self) -> None:
        """Test custom field with default value."""

        def parse_float(value: str) -> float:
            return float(value)

        registry = ModelFieldConverterRegistry()
        registry.register_custom_field("price", parse_float, default=0.0)

        result = registry.convert_field("price", "invalid")
        assert result == 0.0

    def test_convert_field_not_registered(self) -> None:
        """Test converting field that is not registered."""
        registry = ModelFieldConverterRegistry()

        with pytest.raises(ModelOnexError) as exc_info:
            registry.convert_field("unknown_field", "value")
        assert exc_info.value.error_code == EnumCoreErrorCode.NOT_FOUND
        assert "No converter registered" in exc_info.value.message

    def test_convert_data_multiple_fields(self) -> None:
        """Test bulk data conversion with multiple fields."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("enabled")
        registry.register_integer_field("count")
        registry.register_enum_field("status", TestStatus)

        data = {
            "enabled": "true",
            "count": "42",
            "status": "active",
            "unknown_field": "ignored",
        }

        result = registry.convert_data(data)

        # Check converted fields
        assert isinstance(result["enabled"], ModelSchemaValue)
        assert result["enabled"].to_value() is True

        assert isinstance(result["count"], ModelSchemaValue)
        assert result["count"].to_value() == 42

        assert isinstance(result["status"], ModelSchemaValue)
        # ModelSchemaValue stores enums as string representation
        status_value = result["status"].to_value()
        assert status_value == "TestStatus.ACTIVE" or status_value == TestStatus.ACTIVE

        # Unknown field should be skipped
        assert "unknown_field" not in result

    def test_convert_data_empty_dict(self) -> None:
        """Test bulk data conversion with empty dict."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("count")

        result = registry.convert_data({})
        assert result == {}

    def test_convert_data_partial_conversion(self) -> None:
        """Test bulk data conversion with partial field match."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("age")
        # Don't register 'name' field

        data = {"age": "25", "name": "John"}
        result = registry.convert_data(data)

        # Only age should be converted
        assert "age" in result
        assert result["age"].to_value() == 25
        # name should be skipped
        assert "name" not in result

    def test_has_converter(self) -> None:
        """Test has_converter method."""
        registry = ModelFieldConverterRegistry()

        assert not registry.has_converter("test_field")

        registry.register_boolean_field("test_field")
        assert registry.has_converter("test_field")

    def test_list_fields(self) -> None:
        """Test list_fields method."""
        registry = ModelFieldConverterRegistry()

        assert registry.list_fields() == []

        registry.register_boolean_field("enabled")
        registry.register_integer_field("count")
        registry.register_enum_field("status", TestStatus)

        fields = registry.list_fields()
        assert len(fields) == 3
        assert "enabled" in fields
        assert "count" in fields
        assert "status" in fields

    def test_multiple_registrations_same_field(self) -> None:
        """Test that registering same field twice overwrites."""
        registry = ModelFieldConverterRegistry()

        # First registration
        registry.register_integer_field("value", default=0)
        assert registry.convert_field("value", "invalid") == 0

        # Second registration with different default
        registry.register_integer_field("value", default=100)
        assert registry.convert_field("value", "invalid") == 100

    def test_field_converter_frozen_dataclass(self) -> None:
        """Test that FieldConverter is frozen (immutable)."""
        converter = FieldConverter(
            field_name="test",
            converter=int,
        )

        # Should not be able to modify frozen dataclass
        with pytest.raises(Exception):  # FrozenInstanceError in Python 3.11+
            converter.field_name = "modified"  # type: ignore[misc]

    def test_complex_conversion_workflow(self) -> None:
        """Test complex realistic conversion workflow."""
        registry = ModelFieldConverterRegistry()

        # Register various field types
        registry.register_boolean_field("is_active")
        registry.register_integer_field("priority", min_value=1, max_value=10)
        registry.register_enum_field("status", TestStatus, default=TestStatus.PENDING)
        registry.register_optional_integer_field("parent_id")
        registry.register_custom_field("tags", lambda v: v.split(","))

        # Convert realistic data
        data = {
            "is_active": "yes",
            "priority": "5",
            "status": "ACTIVE",
            "parent_id": "123",
            "tags": "bug,high-priority",
            "unknown": "ignored",
        }

        result = registry.convert_data(data)

        # Verify all conversions
        assert result["is_active"].to_value() is True
        assert result["priority"].to_value() == 5
        # ModelSchemaValue stores enums as string representation
        status_value = result["status"].to_value()
        assert status_value == "TestStatus.ACTIVE" or status_value == TestStatus.ACTIVE
        assert result["parent_id"].to_value() == 123
        # Tags are stored as string representation of list
        tags_value = result["tags"].to_value()
        assert (
            tags_value == ["bug", "high-priority"]
            or tags_value == "['bug', 'high-priority']"
        )
        assert "unknown" not in result
