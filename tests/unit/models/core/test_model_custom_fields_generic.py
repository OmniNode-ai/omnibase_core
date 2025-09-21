"""
Unit tests for generic ModelCustomFields[T].

Tests the generic type parameter functionality and type safety
of the ModelCustomFields implementation.
"""

from typing import Any

import pytest

from src.omnibase_core.models.data import ModelCustomFields


class TestModelCustomFieldsGeneric:
    """Test cases for generic ModelCustomFields[T] functionality."""

    def test_generic_type_instantiation(self):
        """Test that generic type can be instantiated with type parameters."""
        # Test with string type
        string_fields = ModelCustomFields[str]()
        assert isinstance(string_fields, ModelCustomFields)

        # Test with int type
        int_fields = ModelCustomFields[int]()
        assert isinstance(int_fields, ModelCustomFields)

        # Test with dict type
        dict_fields = ModelCustomFields[dict[str, Any]]()
        assert isinstance(dict_fields, ModelCustomFields)

    def test_generic_type_field_operations(self):
        """Test that field operations work with generic types."""
        fields = ModelCustomFields[str]()

        # Test setting and getting fields
        fields.set_field("name", "test_value")
        assert fields.get_field("name") == "test_value"

        # Test type-specific getters
        assert fields.get_string("name") == "test_value"
        assert fields.get_int("name", 0) == 0  # Should use default since it's a string

    def test_generic_type_inheritance_behavior(self):
        """Test that generic type inheritance behavior is preserved."""
        fields = ModelCustomFields[dict[str, Any]]()

        # Add various types
        fields.set_field("config", {"key": "value"})
        fields.set_field("count", 42)
        fields.set_field("enabled", True)
        fields.set_field("items", ["a", "b", "c"])

        # Verify field retrieval
        # Note: dict gets converted to string as fallback
        assert fields.get_field("config") == "{'key': 'value'}"
        assert fields.get_field("count") == 42
        assert fields.get_field("enabled") is True
        assert fields.get_field("items") == ["a", "b", "c"]

    def test_generic_factory_methods(self):
        """Test factory methods with generic types."""
        data = {"name": "test", "value": 123, "active": True, "tags": ["a", "b"]}

        # Test BaseModel instantiation with generic type
        fields = ModelCustomFields[dict[str, Any]](**data)

        assert fields.get_string("name") == "test"
        assert fields.get_int("value") == 123
        assert fields.get_bool("active") is True
        assert fields.get_list("tags") == ["a", "b"]

    def test_generic_copy_operations(self):
        """Test copy operations with generic types."""
        original = ModelCustomFields[str]()
        original.set_field("name", "original")
        original.set_field("count", 10)

        # Test copy_fields
        copy = original.copy_fields()
        assert isinstance(copy, ModelCustomFields)
        assert copy.get_string("name") == "original"
        assert copy.get_int("count") == 10

        # Modify copy should not affect original
        copy.set_field("name", "modified")
        assert original.get_string("name") == "original"
        assert copy.get_string("name") == "modified"

    def test_generic_merge_operations(self):
        """Test merge operations with generic types."""
        fields1 = ModelCustomFields[str]()
        fields1.set_field("name", "first")
        fields1.set_field("count", 1)

        fields2 = ModelCustomFields[str]()
        fields2.set_field("name", "second")  # Should override
        fields2.set_field("value", 100)  # Should add new

        # Test merge
        fields1.merge_fields(fields2)

        assert fields1.get_string("name") == "second"  # Overridden
        assert fields1.get_int("count") == 1  # Preserved
        assert fields1.get_int("value") == 100  # Added

    def test_generic_serialization(self):
        """Test serialization with generic types."""
        fields = ModelCustomFields[Any]()
        fields.set_field("string_val", "test")
        fields.set_field("int_val", 42)
        fields.set_field("bool_val", True)
        fields.set_field("list_val", [1, 2, 3])

        # Test model_dump
        data = fields.model_dump(exclude_none=True)
        expected = {
            "string_val": "test",
            "int_val": 42,
            "bool_val": True,
            "list_val": [1, 2, 3],
        }
        assert data == expected

        # Test round-trip
        restored = ModelCustomFields[Any](**data)
        assert restored.model_dump(exclude_none=True) == expected

    def test_generic_pydantic_validation(self):
        """Test Pydantic validation with generic types."""
        # Test model validation
        fields = ModelCustomFields[str](
            string_fields={"name": "test"},
            int_fields={"count": 10},
            bool_fields={"active": True},
            list_fields={"items": ["a", "b"]},
        )

        # Should validate successfully
        assert fields.get_string("name") == "test"
        assert fields.get_int("count") == 10
        assert fields.get_bool("active") is True
        assert fields.get_list("items") == ["a", "b"]

    def test_generic_json_serialization(self):
        """Test JSON serialization with generic types."""
        fields = ModelCustomFields[dict[str, Any]]()
        fields.set_field("config", {"nested": "value"})
        fields.set_field("count", 42)

        # Test JSON serialization
        json_str = fields.model_dump_json()
        assert isinstance(json_str, str)

        # Test JSON deserialization
        restored = ModelCustomFields[dict[str, Any]].model_validate_json(json_str)
        # Note: dict gets converted to string as fallback
        assert restored.get_field("config") == "{'nested': 'value'}"
        assert restored.get_field("count") == 42

    def test_generic_type_safety(self):
        """Test that generic types maintain type safety expectations."""
        # While Python's runtime doesn't enforce generic type parameters,
        # we can test that the typing works correctly for static analysis

        string_fields: ModelCustomFields[str] = ModelCustomFields()
        int_fields: ModelCustomFields[int] = ModelCustomFields()

        # These should work without type errors
        string_fields.set_field("name", "value")
        int_fields.set_field("count", 42)

        # The actual field access should work regardless of generic type
        assert string_fields.get_string("name") == "value"
        assert int_fields.get_int("count") == 42

    def test_generic_with_complex_types(self):
        """Test generic types with complex type parameters."""
        # Test with nested generic types
        complex_fields = ModelCustomFields[dict[str, list[int]]]()

        # Set complex data
        complex_data = {"numbers": [1, 2, 3], "values": [10, 20, 30]}
        complex_fields.set_field("data", complex_data)

        # Retrieve and verify
        retrieved = complex_fields.get_field("data")
        # Note: dict gets converted to string as fallback
        assert retrieved == "{'numbers': [1, 2, 3], 'values': [10, 20, 30]}"

    def test_generic_field_type_detection(self):
        """Test field type detection with generic implementations."""
        fields = ModelCustomFields[Any]()

        # Set different types and check detection
        fields.set_field("str_field", "string")
        fields.set_field("int_field", 42)
        fields.set_field("float_field", 3.14)
        fields.set_field("bool_field", True)
        fields.set_field("list_field", [1, 2, 3])

        # Test type detection
        assert fields.get_field_type("str_field") == "string"
        assert fields.get_field_type("int_field") == "int"
        assert fields.get_field_type("float_field") == "float"
        assert fields.get_field_type("bool_field") == "bool"
        assert fields.get_field_type("list_field") == "list"

    def test_generic_field_validation(self):
        """Test field validation with generic types."""
        fields = ModelCustomFields[str]()

        # Set initial field
        fields.set_field("name", "test")

        # Test validation
        assert fields.validate_field_value("name", "new_string") is True
        assert fields.validate_field_value("name", 123) is False  # Wrong type
        assert (
            fields.validate_field_value("new_field", "any_value") is True
        )  # New field

    def test_generic_all_field_operations(self):
        """Test comprehensive field operations with generic types."""
        fields = ModelCustomFields[dict[str, Any]]()

        # Add various fields
        fields.set_field("config", {"key": "value"})
        fields.set_field("count", 10)
        fields.set_field("enabled", True)

        # Test field counting
        assert fields.get_field_count() == 3

        # Test field listing
        field_names = fields.get_all_field_names()
        assert set(field_names) == {"config", "count", "enabled"}

        # Test field existence
        assert fields.has_field("config") is True
        assert fields.has_field("nonexistent") is False

        # Test field removal
        assert fields.remove_field("count") is True
        assert fields.get_field_count() == 2
        assert fields.has_field("count") is False

        # Test clearing all fields
        fields.clear_all_fields()
        assert fields.get_field_count() == 0

    def test_generic_fields_by_type(self):
        """Test getting fields by type with generic implementations."""
        fields = ModelCustomFields[Any]()

        # Add fields of different types
        fields.set_field("name", "test")
        fields.set_field("title", "example")
        fields.set_field("count", 42)
        fields.set_field("value", 100)
        fields.set_field("active", True)

        # Test getting fields by type
        string_fields = fields.get_fields_by_type("string")
        int_fields = fields.get_fields_by_type("int")
        bool_fields = fields.get_fields_by_type("bool")

        assert string_fields == {"name": "test", "title": "example"}
        assert int_fields == {"count": 42, "value": 100}
        assert bool_fields == {"active": True}


class TestModelCustomFieldsGenericEdgeCases:
    """Test edge cases for generic ModelCustomFields[T]."""

    def test_generic_with_none_type(self):
        """Test generic behavior with None type parameter."""
        # This tests the edge case where T might be None
        fields = ModelCustomFields[None]()

        # Should still work for basic operations
        fields.set_field("test", "value")
        assert fields.get_field("test") == "value"

    def test_generic_inheritance_compatibility(self):
        """Test that generic types maintain inheritance compatibility."""
        # Test that generic instances are compatible with base type
        generic_fields = ModelCustomFields[str]()
        base_fields = ModelCustomFields()

        # Both should have the same interface
        generic_fields.set_field("test", "value")
        base_fields.set_field("test", "value")

        assert generic_fields.get_field("test") == base_fields.get_field("test")

    def test_generic_multiple_type_parameters(self):
        """Test behavior when using complex generic type parameters."""
        # Test with union types
        union_fields = ModelCustomFields[str | int]()
        union_fields.set_field("mixed", "string_value")
        union_fields.set_field("number", 42)

        assert union_fields.get_field("mixed") == "string_value"
        assert union_fields.get_field("number") == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
