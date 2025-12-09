"""
Tests for ModelFieldConverterRegistry - Registry for field converters.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.utils.model_field_converter_registry import (
    ModelFieldConverterRegistry,
)


# Sample enum for testing enum field conversion
class SampleStatus(Enum):
    """Sample enum for enum field conversion."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class TestModelFieldConverterRegistryInit:
    """Test ModelFieldConverterRegistry initialization."""

    def test_init_creates_empty_registry(self):
        """Test initialization creates empty converter registry."""
        registry = ModelFieldConverterRegistry()
        assert registry._converters == {}
        assert registry.list_fields() == []


class TestRegisterBooleanField:
    """Test boolean field registration."""

    def test_register_boolean_field_default_values(self):
        """Test register_boolean_field() with default true values."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("is_active")

        assert registry.convert_field("is_active", "true") is True
        assert registry.convert_field("is_active", "1") is True
        assert registry.convert_field("is_active", "yes") is True
        assert registry.convert_field("is_active", "on") is True
        assert registry.convert_field("is_active", "false") is False
        assert registry.convert_field("is_active", "0") is False

    def test_register_boolean_field_custom_true_values(self):
        """Test register_boolean_field() with custom true values."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("enabled", true_values={"enabled", "on"})

        assert registry.convert_field("enabled", "enabled") is True
        assert registry.convert_field("enabled", "on") is True
        assert registry.convert_field("enabled", "true") is False

    def test_register_boolean_field_case_insensitive(self):
        """Test boolean conversion is case-insensitive."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("flag")

        assert registry.convert_field("flag", "TRUE") is True
        assert registry.convert_field("flag", "True") is True
        assert registry.convert_field("flag", "YES") is True
        assert registry.convert_field("flag", "On") is True

    def test_register_boolean_field_with_default(self):
        """Test register_boolean_field() with default value."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("optional", default=False)

        assert registry.has_converter("optional")


class TestRegisterIntegerField:
    """Test integer field registration."""

    def test_register_integer_field_basic(self):
        """Test register_integer_field() basic functionality."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("age")

        assert registry.convert_field("age", "25") == 25
        assert registry.convert_field("age", "0") == 0
        assert registry.convert_field("age", "-5") == -5

    def test_register_integer_field_with_min_value(self):
        """Test register_integer_field() with min_value validation."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("port", min_value=1024)

        # Min value validation happens in FieldConverter, not during registration
        # This test just ensures the field is registered
        assert registry.has_converter("port")

    def test_register_integer_field_with_max_value(self):
        """Test register_integer_field() with max_value validation."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("percentage", max_value=100)

        assert registry.has_converter("percentage")

    def test_register_integer_field_with_range(self):
        """Test register_integer_field() with min and max values."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("score", min_value=0, max_value=100)

        assert registry.has_converter("score")

    def test_register_integer_field_with_default(self):
        """Test register_integer_field() with default value."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("timeout", default=30)

        assert registry.has_converter("timeout")

    def test_register_integer_field_conversion_error(self):
        """Test integer conversion raises error on invalid input."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("count")

        # FieldConverter wraps ValueError in ModelOnexError
        with pytest.raises(ModelOnexError) as exc_info:
            registry.convert_field("count", "not_a_number")
        assert exc_info.value.error_code == EnumCoreErrorCode.CONVERSION_ERROR


class TestRegisterEnumField:
    """Test enum field registration."""

    def test_register_enum_field_by_value(self):
        """Test enum conversion by exact value match."""
        registry = ModelFieldConverterRegistry()
        registry.register_enum_field("status", SampleStatus)

        result = registry.convert_field("status", "active")
        assert result == SampleStatus.ACTIVE

        result = registry.convert_field("status", "inactive")
        assert result == SampleStatus.INACTIVE

    def test_register_enum_field_by_name_case_insensitive(self):
        """Test enum conversion by name (case-insensitive)."""
        registry = ModelFieldConverterRegistry()
        registry.register_enum_field("status", SampleStatus)

        result = registry.convert_field("status", "ACTIVE")
        assert result == SampleStatus.ACTIVE

        result = registry.convert_field("status", "Active")
        assert result == SampleStatus.ACTIVE

        result = registry.convert_field("status", "inactive")
        assert result == SampleStatus.INACTIVE

    def test_register_enum_field_with_default(self):
        """Test enum field with default value for invalid inputs."""
        registry = ModelFieldConverterRegistry()
        registry.register_enum_field(
            "status", SampleStatus, default=SampleStatus.PENDING
        )

        # Valid value
        result = registry.convert_field("status", "active")
        assert result == SampleStatus.ACTIVE

        # Invalid value returns default
        result = registry.convert_field("status", "invalid")
        assert result == SampleStatus.PENDING

    def test_register_enum_field_without_default_raises_error(self):
        """Test enum field without default raises error on invalid input."""
        registry = ModelFieldConverterRegistry()
        registry.register_enum_field("status", SampleStatus)

        with pytest.raises(ModelOnexError) as exc_info:
            registry.convert_field("status", "invalid")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid SampleStatus value" in exc_info.value.message


class TestRegisterOptionalIntegerField:
    """Test optional integer field registration."""

    def test_register_optional_integer_field_valid_value(self):
        """Test optional integer field with valid value."""
        registry = ModelFieldConverterRegistry()
        registry.register_optional_integer_field("count")

        assert registry.convert_field("count", "42") == 42
        assert registry.convert_field("count", "100") == 100

    def test_register_optional_integer_field_empty_string(self):
        """Test optional integer field returns None for empty string."""
        registry = ModelFieldConverterRegistry()
        registry.register_optional_integer_field("count")

        assert registry.convert_field("count", "") is None

    def test_register_optional_integer_field_zero_as_none(self):
        """Test optional integer field with zero_as_none=True."""
        registry = ModelFieldConverterRegistry()
        registry.register_optional_integer_field("count", zero_as_none=True)

        assert registry.convert_field("count", "0") is None
        assert registry.convert_field("count", "1") == 1

    def test_register_optional_integer_field_zero_as_value(self):
        """Test optional integer field with zero_as_none=False."""
        registry = ModelFieldConverterRegistry()
        registry.register_optional_integer_field("count", zero_as_none=False)

        assert registry.convert_field("count", "0") == 0
        assert registry.convert_field("count", "1") == 1


class TestRegisterCustomField:
    """Test custom field registration."""

    def test_register_custom_field_basic(self):
        """Test register_custom_field() with simple converter."""
        registry = ModelFieldConverterRegistry()

        def uppercase_converter(value: str) -> str:
            return value.upper()

        registry.register_custom_field("name", uppercase_converter)

        assert registry.convert_field("name", "john") == "JOHN"
        assert registry.convert_field("name", "jane") == "JANE"

    def test_register_custom_field_with_default(self):
        """Test register_custom_field() with default value."""
        registry = ModelFieldConverterRegistry()

        def length_converter(value: str) -> int:
            return len(value)

        registry.register_custom_field("length", length_converter, default=0)

        assert registry.convert_field("length", "hello") == 5
        assert registry.has_converter("length")

    def test_register_custom_field_with_validator(self):
        """Test register_custom_field() with validator."""
        registry = ModelFieldConverterRegistry()

        def parse_port(value: str) -> int:
            return int(value)

        def validate_port(value: object) -> bool:
            return isinstance(value, int) and 1024 <= value <= 65535

        registry.register_custom_field("port", parse_port, validator=validate_port)

        assert registry.convert_field("port", "8080") == 8080


class TestConvertField:
    """Test convert_field() method."""

    def test_convert_field_raises_error_for_unregistered_field(self):
        """Test convert_field() raises error for unregistered field."""
        registry = ModelFieldConverterRegistry()

        with pytest.raises(ModelOnexError) as exc_info:
            registry.convert_field("unknown_field", "value")

        assert exc_info.value.error_code == EnumCoreErrorCode.NOT_FOUND
        assert "No converter registered for field" in exc_info.value.message

    def test_convert_field_with_registered_field(self):
        """Test convert_field() works with registered field."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("age")

        result = registry.convert_field("age", "30")
        assert result == 30


class TestConvertData:
    """Test convert_data() method."""

    def test_convert_data_empty_dict(self):
        """Test convert_data() with empty dictionary."""
        registry = ModelFieldConverterRegistry()
        result = registry.convert_data({})
        assert result == {}

    def test_convert_data_with_registered_fields(self):
        """Test convert_data() converts registered fields."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("is_active")
        registry.register_integer_field("age")
        registry.register_enum_field("status", SampleStatus)

        data = {"is_active": "true", "age": "25", "status": "active"}

        result = registry.convert_data(data)

        assert result["is_active"].to_value() is True
        assert result["age"].to_value() == 25
        # ModelSchemaValue.from_value() converts enum to string representation
        assert "ACTIVE" in str(result["status"].to_value())

    def test_convert_data_skips_unregistered_fields(self):
        """Test convert_data() skips fields without converters."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("age")

        data = {"age": "25", "unknown_field": "value"}

        result = registry.convert_data(data)

        assert "age" in result
        assert "unknown_field" not in result

    def test_convert_data_mixed_fields(self):
        """Test convert_data() with mix of registered and unregistered fields."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("enabled")
        registry.register_integer_field("count")

        data = {
            "enabled": "true",
            "count": "10",
            "extra1": "ignored",
            "extra2": "also_ignored",
        }

        result = registry.convert_data(data)

        assert len(result) == 2
        assert result["enabled"].to_value() is True
        assert result["count"].to_value() == 10


class TestHasConverter:
    """Test has_converter() method."""

    def test_has_converter_for_registered_field(self):
        """Test has_converter() returns True for registered field."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("flag")

        assert registry.has_converter("flag") is True

    def test_has_converter_for_unregistered_field(self):
        """Test has_converter() returns False for unregistered field."""
        registry = ModelFieldConverterRegistry()
        assert registry.has_converter("unknown") is False

    def test_has_converter_multiple_fields(self):
        """Test has_converter() with multiple registered fields."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("flag1")
        registry.register_integer_field("num1")
        registry.register_enum_field("status", SampleStatus)

        assert registry.has_converter("flag1") is True
        assert registry.has_converter("num1") is True
        assert registry.has_converter("status") is True
        assert registry.has_converter("unknown") is False


class TestListFields:
    """Test list_fields() method."""

    def test_list_fields_empty_registry(self):
        """Test list_fields() returns empty list for empty registry."""
        registry = ModelFieldConverterRegistry()
        assert registry.list_fields() == []

    def test_list_fields_with_registered_fields(self):
        """Test list_fields() returns all registered field names."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("enabled")
        registry.register_integer_field("count")
        registry.register_enum_field("status", SampleStatus)

        fields = registry.list_fields()

        assert len(fields) == 3
        assert "enabled" in fields
        assert "count" in fields
        assert "status" in fields

    def test_list_fields_order_independent(self):
        """Test list_fields() returns all fields regardless of order."""
        registry = ModelFieldConverterRegistry()
        registry.register_boolean_field("field_a")
        registry.register_integer_field("field_b")
        registry.register_custom_field("field_c", lambda x: x)

        fields = set(registry.list_fields())
        expected = {"field_a", "field_b", "field_c"}

        assert fields == expected


class TestModelFieldConverterRegistryIntegration:
    """Integration tests for ModelFieldConverterRegistry."""

    def test_complete_workflow(self):
        """Test complete workflow from registration to conversion."""
        registry = ModelFieldConverterRegistry()

        # Register various field types
        registry.register_boolean_field("is_active", default=True)
        registry.register_integer_field("age", min_value=0, max_value=120)
        registry.register_enum_field(
            "status", SampleStatus, default=SampleStatus.PENDING
        )
        registry.register_optional_integer_field("score", zero_as_none=True)

        # Verify all registered
        assert len(registry.list_fields()) == 4

        # Convert individual fields
        assert registry.convert_field("is_active", "true") is True
        assert registry.convert_field("age", "30") == 30
        assert registry.convert_field("status", "active") == SampleStatus.ACTIVE
        assert registry.convert_field("score", "0") is None

        # Convert batch data
        data = {"is_active": "yes", "age": "25", "status": "inactive", "score": "95"}

        result = registry.convert_data(data)

        assert result["is_active"].to_value() is True
        assert result["age"].to_value() == 25
        # ModelSchemaValue.from_value() converts enum to string representation
        assert "INACTIVE" in str(result["status"].to_value())
        assert result["score"].to_value() == 95

    def test_multiple_registries_independent(self):
        """Test multiple registry instances are independent."""
        registry1 = ModelFieldConverterRegistry()
        registry2 = ModelFieldConverterRegistry()

        registry1.register_boolean_field("flag")
        registry2.register_integer_field("count")

        assert registry1.has_converter("flag") is True
        assert registry1.has_converter("count") is False

        assert registry2.has_converter("flag") is False
        assert registry2.has_converter("count") is True

    def test_error_handling_in_batch_conversion(self):
        """Test error handling when batch conversion encounters issues."""
        registry = ModelFieldConverterRegistry()
        registry.register_integer_field("valid")
        registry.register_integer_field("invalid")

        # This will cause the invalid field conversion to fail
        # FieldConverter wraps ValueError in ModelOnexError
        with pytest.raises(ModelOnexError) as exc_info:
            registry.convert_data({"valid": "123", "invalid": "not_a_number"})
        assert exc_info.value.error_code == EnumCoreErrorCode.CONVERSION_ERROR
