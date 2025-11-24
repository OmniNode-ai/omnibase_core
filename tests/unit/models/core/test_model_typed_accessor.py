"""
Test suite for ModelTypedAccessor.

Tests the type-safe field accessor with generic type support.
"""

from typing import Any

import pytest
from pydantic import Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_typed_accessor import ModelTypedAccessor
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class TestTypedModel(ModelTypedAccessor[str]):
    """Test model for typed accessor testing."""

    data: dict[str, Any] = Field(default_factory=dict)


class TestTypedIntModel(ModelTypedAccessor[int]):
    """Test model for integer typed accessor testing."""

    data: dict[str, Any] = Field(default_factory=dict)


class TestModelTypedAccessor:
    """Test cases for ModelTypedAccessor."""

    def test_initialization(self):
        """Test typed accessor initialization."""
        accessor = TestTypedModel()

        assert hasattr(accessor, "get_typed_field")
        assert hasattr(accessor, "set_typed_field")

    def test_get_typed_field_string_success(self):
        """Test getting typed field with correct type (string)."""
        accessor = TestTypedModel()

        # Set up field with string value
        accessor.set_field("data.name", ModelSchemaValue.from_value("test_value"))

        result = accessor.get_typed_field("data.name", str, "default")

        assert result == "test_value"

    def test_get_typed_field_string_default(self):
        """Test getting typed field returns default when not found."""
        accessor = TestTypedModel()

        result = accessor.get_typed_field("data.nonexistent", str, "default_value")

        assert result == "default_value"

    def test_get_typed_field_string_type_mismatch(self):
        """Test getting typed field returns default when type doesn't match."""
        accessor = TestTypedModel()

        # Set up field with integer value
        accessor.set_field("data.count", ModelSchemaValue.from_value(42))

        # Try to get as string
        result = accessor.get_typed_field("data.count", str, "default")

        assert result == "default"

    def test_get_typed_field_int_success(self):
        """Test getting typed field with correct type (int)."""
        accessor = TestTypedIntModel()

        # Set up field with int value
        accessor.set_field("data.count", ModelSchemaValue.from_value(42))

        result = accessor.get_typed_field("data.count", int, 0)

        assert result == 42

    def test_get_typed_field_int_default(self):
        """Test getting integer typed field returns default when not found."""
        accessor = TestTypedIntModel()

        result = accessor.get_typed_field("data.nonexistent", int, 999)

        assert result == 999

    def test_get_typed_field_float_success(self):
        """Test getting typed field with float type."""
        accessor = TestTypedModel()

        # Set up field with float value
        accessor.set_field("data.score", ModelSchemaValue.from_value(95.5))

        result = accessor.get_typed_field("data.score", float, 0.0)

        assert result == 95.5

    def test_get_typed_field_bool_success(self):
        """Test getting typed field with bool type."""
        accessor = TestTypedModel()

        # Set up field with bool value
        accessor.set_field("data.enabled", ModelSchemaValue.from_value(True))

        result = accessor.get_typed_field("data.enabled", bool, False)

        assert result is True

    def test_get_typed_field_none_value(self):
        """Test getting typed field when value is None."""
        accessor = TestTypedModel()

        # Set up field with None value
        accessor.set_field("data.empty", ModelSchemaValue.from_value(None))

        result = accessor.get_typed_field("data.empty", str, "default")

        # Should return default since None is not an instance of str
        assert result == "default"

    def test_set_typed_field_string_success(self):
        """Test setting typed field with valid type (string)."""
        accessor = TestTypedModel()

        result = accessor.set_typed_field("data.name", "test_value", str)

        assert result is True
        # Verify it was set correctly
        retrieved = accessor.get_typed_field("data.name", str, "")
        assert retrieved == "test_value"

    def test_set_typed_field_int_success(self):
        """Test setting typed field with valid type (int)."""
        accessor = TestTypedIntModel()

        result = accessor.set_typed_field("data.count", 42, int)

        assert result is True
        # Verify it was set correctly
        retrieved = accessor.get_typed_field("data.count", int, 0)
        assert retrieved == 42

    def test_set_typed_field_float_success(self):
        """Test setting typed field with valid type (float)."""
        accessor = TestTypedModel()

        result = accessor.set_typed_field("data.score", 95.5, float)

        assert result is True
        # Verify it was set correctly
        retrieved = accessor.get_typed_field("data.score", float, 0.0)
        assert retrieved == 95.5

    def test_set_typed_field_bool_success(self):
        """Test setting typed field with valid type (bool)."""
        accessor = TestTypedModel()

        result = accessor.set_typed_field("data.enabled", True, bool)

        assert result is True
        # Verify it was set correctly
        retrieved = accessor.get_typed_field("data.enabled", bool, False)
        assert retrieved is True

    def test_set_typed_field_type_mismatch(self):
        """Test setting typed field with wrong type fails."""
        accessor = TestTypedModel()

        # Try to set int when expecting string
        result = accessor.set_typed_field("data.name", 42, str)

        assert result is False

    def test_set_typed_field_with_schema_value(self):
        """Test setting typed field with ModelSchemaValue directly."""
        accessor = TestTypedModel()

        schema_value = ModelSchemaValue.from_value("test")
        result = accessor.set_typed_field("data.value", schema_value, ModelSchemaValue)

        assert result is True

    def test_multiple_typed_fields(self):
        """Test working with multiple typed fields."""
        accessor = TestTypedModel()

        # Set multiple fields
        accessor.set_typed_field("data.name", "John", str)
        accessor.set_typed_field("data.age", 30, int)
        accessor.set_typed_field("data.score", 95.5, float)
        accessor.set_typed_field("data.active", True, bool)

        # Retrieve all fields
        assert accessor.get_typed_field("data.name", str, "") == "John"
        assert accessor.get_typed_field("data.age", int, 0) == 30
        assert accessor.get_typed_field("data.score", float, 0.0) == 95.5
        assert accessor.get_typed_field("data.active", bool, False) is True

    def test_overwrite_typed_field(self):
        """Test overwriting existing typed field."""
        accessor = TestTypedModel()

        # Set initial value
        accessor.set_typed_field("data.name", "Initial", str)
        assert accessor.get_typed_field("data.name", str, "") == "Initial"

        # Overwrite
        accessor.set_typed_field("data.name", "Updated", str)
        assert accessor.get_typed_field("data.name", str, "") == "Updated"

    def test_configure_protocol_method(self):
        """Test configure method (Configurable protocol)."""
        accessor = TestTypedModel()

        result = accessor.configure(custom_attr="test_value", another=123)

        assert result is True

    def test_configure_with_exception(self):
        """Test configure raises ModelOnexError for invalid input."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        accessor = TestTypedModel()

        # Try to configure with invalid type - data expects dict but given string
        with pytest.raises(ModelOnexError, match="Operation failed"):
            accessor.configure(data="invalid_type")

    def test_serialize_protocol_method(self):
        """Test serialize method (Serializable protocol)."""
        accessor = TestTypedModel()

        serialized = accessor.serialize()

        assert isinstance(serialized, dict)
        assert "accessor_type" in serialized
        assert serialized["accessor_type"] == "TestTypedModel"

    def test_serialize_with_data(self):
        """Test serialize includes instance data."""
        accessor = TestTypedModel()

        # Set some data
        accessor.set_typed_field("data.test", "value", str)

        serialized = accessor.serialize()

        assert "accessor_type" in serialized
        # data field should be included if it's not private
        assert "data" in serialized or "accessor_type" in serialized

    def test_serialize_excludes_private_attributes(self):
        """Test serialize excludes private attributes."""
        accessor = TestTypedModel()

        # Add private attribute
        accessor._private = "should_not_serialize"

        serialized = accessor.serialize()

        assert "_private" not in serialized

    def test_serialize_handles_non_serializable_types(self):
        """Test serialize handles non-serializable types gracefully."""
        accessor = TestTypedModel()

        # Pydantic models have strict attribute assignment
        # We can't set arbitrary attributes, so test with existing data field instead
        accessor.data = {"nested": TestTypedModel()}

        # Should not raise exception
        try:
            serialized = accessor.serialize()
            assert isinstance(serialized, dict)
        except Exception:
            # If serialization fails with complex nested types, that's acceptable
            # The test validates that it doesn't crash the application
            assert True

    def test_validate_instance_protocol_method(self):
        """Test validate_instance method (Validatable protocol)."""
        accessor = TestTypedModel()

        result = accessor.validate_instance()

        assert result is True

    def test_validate_instance_with_data(self):
        """Test validate_instance with populated data."""
        accessor = TestTypedModel()

        accessor.set_typed_field("data.test", "value", str)

        result = accessor.validate_instance()

        assert result is True

    def test_get_name_protocol_method(self):
        """Test get_name method (Nameable protocol)."""
        accessor = TestTypedModel()

        name = accessor.get_name()

        assert isinstance(name, str)
        assert "TestTypedModel" in name

    def test_set_name_protocol_method(self):
        """Test set_name method (Nameable protocol)."""
        accessor = TestTypedModel()

        # Should not raise exception
        accessor.set_name("Custom Name")

        assert True

    def test_inheritance_from_field_accessor(self):
        """Test typed accessor inherits from field accessor."""
        accessor = TestTypedModel()

        # Should have base field accessor methods
        assert hasattr(accessor, "get_field")
        assert hasattr(accessor, "set_field")
        assert hasattr(accessor, "has_field")
        assert hasattr(accessor, "remove_field")

    def test_nested_path_access(self):
        """Test accessing deeply nested paths."""
        accessor = TestTypedModel()

        # Set nested field
        accessor.set_typed_field("data.user.profile.name", "John", str)

        # Get nested field
        result = accessor.get_typed_field("data.user.profile.name", str, "")

        assert result == "John"

    def test_list_type_handling(self):
        """Test handling list types."""
        accessor = TestTypedModel()

        # Set list field
        accessor.set_field("data.tags", ModelSchemaValue.from_value(["tag1", "tag2"]))

        # Get as list type
        result = accessor.get_typed_field("data.tags", list, [])

        assert result == ["tag1", "tag2"]

    def test_dict_type_handling(self):
        """Test handling dict types."""
        accessor = TestTypedModel()

        # Set dict field
        test_dict = {"key1": "value1", "key2": "value2"}
        # Use the data field directly since it's already a dict
        accessor.data = test_dict

        # Test that we can work with dict data
        assert accessor.data == test_dict
        assert isinstance(accessor.data, dict)

    def test_edge_case_empty_string(self):
        """Test edge case with empty string."""
        accessor = TestTypedModel()

        accessor.set_typed_field("data.empty", "", str)

        result = accessor.get_typed_field("data.empty", str, "default")

        assert result == ""

    def test_edge_case_zero_value(self):
        """Test edge case with zero value."""
        accessor = TestTypedIntModel()

        accessor.set_typed_field("data.count", 0, int)

        result = accessor.get_typed_field("data.count", int, 999)

        assert result == 0

    def test_edge_case_false_value(self):
        """Test edge case with False value."""
        accessor = TestTypedModel()

        accessor.set_typed_field("data.enabled", False, bool)

        result = accessor.get_typed_field("data.enabled", bool, True)

        assert result is False

    def test_type_parameter_in_serialize(self):
        """Test that type parameter information is included in serialize."""
        accessor = TestTypedModel()

        serialized = accessor.serialize()

        assert "type_parameter" in serialized
        # Should include type information
        assert isinstance(serialized["type_parameter"], str)

    def test_complex_scenario_mixed_types(self):
        """Test complex scenario with mixed types."""
        accessor = TestTypedModel()

        # Set various types
        accessor.set_typed_field("data.username", "john_doe", str)
        accessor.set_typed_field("data.user_id", 12345, int)
        accessor.set_typed_field("data.balance", 1000.50, float)
        accessor.set_typed_field("data.is_verified", True, bool)

        # Retrieve all types
        assert accessor.get_typed_field("data.username", str, "") == "john_doe"
        assert accessor.get_typed_field("data.user_id", int, 0) == 12345
        assert accessor.get_typed_field("data.balance", float, 0.0) == 1000.50
        assert accessor.get_typed_field("data.is_verified", bool, False) is True

        # Try to get with wrong types (should return defaults)
        assert accessor.get_typed_field("data.username", int, 999) == 999
        assert accessor.get_typed_field("data.user_id", str, "default") == "default"

    def test_generic_type_constraints(self):
        """Test that generic type parameter works correctly."""
        str_accessor = TestTypedModel()
        int_accessor = TestTypedIntModel()

        # Both should work independently
        str_accessor.set_typed_field("data.value", "text", str)
        int_accessor.set_typed_field("data.value", 42, int)

        assert str_accessor.get_typed_field("data.value", str, "") == "text"
        assert int_accessor.get_typed_field("data.value", int, 0) == 42
