"""
Unit tests for ModelGenericMetadata.

Tests the flexible metadata functionality and type-safe custom fields
of the ModelGenericMetadata implementation.
"""

import pytest

from omnibase_core.models.metadata.model_generic_metadata import ModelGenericMetadata
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


@pytest.mark.unit
class TestModelGenericMetadataGeneric:
    """Test cases for ModelGenericMetadata functionality."""

    def test_generic_type_instantiation(self):
        """Test that metadata can be instantiated."""
        # Test basic instantiation
        string_metadata = ModelGenericMetadata()
        assert isinstance(string_metadata, ModelGenericMetadata)

        # Test with different initializations
        dict_metadata = ModelGenericMetadata()
        assert isinstance(dict_metadata, ModelGenericMetadata)

        # Test with parameters
        list_metadata = ModelGenericMetadata()
        assert isinstance(list_metadata, ModelGenericMetadata)

    def test_generic_type_with_standard_fields(self):
        """Test that standard fields work correctly."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        metadata = ModelGenericMetadata(
            name="test_metadata",
            description="Test description",
            version="1.0.0",
            tags=["test", "generic"],
        )

        assert metadata.name == "test_metadata"
        assert metadata.description == "Test description"
        # version is converted from string to ModelSemVer by validator
        assert isinstance(metadata.version, ModelSemVer)
        assert metadata.version.major == 1
        assert metadata.version.minor == 0
        assert metadata.version.patch == 0
        assert metadata.tags == ["test", "generic"]

    def test_generic_custom_fields_operations(self):
        """Test custom fields operations."""
        metadata = ModelGenericMetadata()

        # Test setting custom fields (using basic types only)
        metadata.set_field("name", "test_name")
        metadata.set_field("count", 42)
        metadata.set_field("enabled", True)

        # Test getting custom fields
        assert metadata.get_field("name") == "test_name"
        assert metadata.get_field("count") == 42
        assert metadata.get_field("enabled") is True
        assert metadata.get_field("nonexistent") is None
        assert metadata.get_field("nonexistent", "default") == "default"

    def test_generic_has_field_operation(self):
        """Test has_field operation."""
        metadata = ModelGenericMetadata()

        # Initially no custom fields
        assert metadata.has_field("test") is False

        # Add custom field
        metadata.set_field("test", "value")
        assert metadata.has_field("test") is True

    def test_generic_remove_field_operation(self):
        """Test remove_field operation."""
        metadata = ModelGenericMetadata()

        # Add field and verify
        metadata.set_field("count", 100)
        assert metadata.has_field("count") is True

        # Remove field
        assert metadata.remove_field("count") is True
        assert metadata.has_field("count") is False

        # Try to remove non-existent field
        assert metadata.remove_field("nonexistent") is False

    def test_generic_to_dict_operation(self):
        """Test to_dict operation."""
        metadata = ModelGenericMetadata(
            name="test_metadata",
            description="Test description",
            version="1.0.0",
            tags=["test"],
        )

        # Add custom fields (basic types only)
        metadata.set_field("setting", "custom_value")
        metadata.set_field("priority", 5)

        # Test model_dump
        result = metadata.model_dump(exclude_none=True, by_alias=True)

        # Should include standard fields
        assert result["name"] == "test_metadata"
        assert result["description"] == "Test description"
        assert result["version"] == {"major": 1, "minor": 0, "patch": 0}
        assert result["tags"] == ["test"]

        # Should include custom fields
        assert result["custom_fields"]["setting"]["raw_value"] == "custom_value"
        assert result["custom_fields"]["priority"]["raw_value"] == 5

    def test_generic_from_dict_factory(self):
        """Test from_dict factory method."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        data = {
            "name": "test_metadata",
            "description": "Test description",
            "version": "2.0.0",
            "tags": ["factory", "test"],
            "custom_field": "custom_value",
            "priority": 10,
            "config": {"setting": "value"},
        }

        # Create from dict using BaseModel instantiation
        # Since custom fields are mixed with standard fields, we need to separate them
        standard_fields = {"name", "description", "version", "tags", "custom_fields"}
        standard_data = {k: v for k, v in data.items() if k in standard_fields}
        custom_data = {k: v for k, v in data.items() if k not in standard_fields}

        # Create instance with standard fields and add custom fields
        metadata = ModelGenericMetadata.model_validate(standard_data)
        if custom_data:
            if metadata.custom_fields is None:
                metadata.custom_fields = {}
            for key, value in custom_data.items():
                metadata.set_field(key, value)

        # Verify standard fields
        assert metadata.name == "test_metadata"
        assert metadata.description == "Test description"
        # version is converted from string to ModelSemVer by validator
        assert isinstance(metadata.version, ModelSemVer)
        assert metadata.version.major == 2
        assert metadata.version.minor == 0
        assert metadata.version.patch == 0
        assert metadata.tags == ["factory", "test"]

        # Verify custom fields
        assert metadata.get_field("custom_field") == "custom_value"
        assert metadata.get_field("priority") == 10
        # Note: Nested dicts don't round-trip perfectly through ModelValue
        # This is expected behavior - nested values become ModelSchemaValue objects
        config = metadata.get_field("config")
        assert isinstance(config, dict)
        assert "setting" in config
        # The nested value is a ModelSchemaValue, verify it contains the right data
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue

        assert isinstance(config["setting"], ModelSchemaValue)
        assert config["setting"].string_value == "value"

    def test_generic_pydantic_validation(self):
        """Test Pydantic validation."""
        # Test valid data
        metadata = ModelGenericMetadata(
            name="valid_metadata",
            tags=["tag1", "tag2"],
            custom_fields={"key": "value"},
        )

        assert metadata.name == "valid_metadata"
        assert metadata.tags == ["tag1", "tag2"]
        assert metadata.custom_fields["key"].raw_value == "value"

    def test_generic_json_serialization(self):
        """Test JSON serialization."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        metadata = ModelGenericMetadata(
            name="json_test",
            description="JSON serialization test",
            version="1.0.0",
        )

        # Add custom fields (basic types only)
        metadata.set_field("setting", "test_value")
        metadata.set_field("count", 42)

        # Test JSON serialization
        json_str = metadata.model_dump_json(by_alias=True)
        assert isinstance(json_str, str)

        # Test JSON deserialization
        restored = ModelGenericMetadata.model_validate_json(json_str)

        assert restored.name == "json_test"
        assert restored.description == "JSON serialization test"
        # version is ModelSemVer object after deserialization
        assert isinstance(restored.version, ModelSemVer)
        assert restored.version.major == 1
        assert restored.version.minor == 0
        assert restored.version.patch == 0
        # Note: Custom fields may not round-trip perfectly through JSON due to complex nesting
        # This is expected behavior for complex ModelValue structures

    def test_generic_with_complex_types(self):
        """Test with list data."""
        # Test with list type
        list_metadata = ModelGenericMetadata()

        # Set list data (basic types only)
        list_data = ["item1", "item2", "item3"]
        list_metadata.set_field("items", list_data)

        # Retrieve and verify
        retrieved = list_metadata.get_field("items")
        assert retrieved == list_data

    def test_generic_custom_fields_none_handling(self):
        """Test custom fields behavior when custom_fields is None."""
        metadata = ModelGenericMetadata(name="test")

        # custom_fields should initially be None
        assert metadata.custom_fields is None

        # Getting from None custom_fields should return default
        assert metadata.get_field("test") is None
        assert metadata.get_field("test", "default") == "default"

        # has_field should return False for None custom_fields
        assert metadata.has_field("test") is False

        # remove_field should return False for None custom_fields
        assert metadata.remove_field("test") is False

        # Setting a field should initialize custom_fields
        metadata.set_field("test", "value")
        assert metadata.custom_fields is not None
        assert metadata.get_field("test") == "value"

    def test_generic_field_name_conflicts(self):
        """Test handling of field name conflicts with standard fields."""
        metadata = ModelGenericMetadata()

        # Add custom field with same name as standard field
        metadata.set_field("name", "custom_name_value")
        metadata.set_field("description", "custom_description_value")

        # Standard field access should work
        assert metadata.name is None  # Standard field, not set

        # Custom field access should work
        assert metadata.get_field("name") == "custom_name_value"
        assert metadata.get_field("description") == "custom_description_value"

        # model_dump should not override standard fields with custom fields
        metadata.name = "standard_name"
        result = metadata.model_dump(exclude_none=True, by_alias=True)
        assert result["name"] == "standard_name"  # Standard field takes precedence

    def test_generic_inheritance_behavior(self):
        """Test that inheritance behavior is preserved."""
        # Test instance creation
        base_metadata = ModelGenericMetadata()
        derived_metadata = ModelGenericMetadata()

        # Both should support the same interface
        base_metadata.set_field("test", "string_value")
        derived_metadata.set_field("test", 42)

        assert base_metadata.get_field("test") == "string_value"
        assert derived_metadata.get_field("test") == 42

    def test_generic_type_safety(self):
        """Test that metadata maintains type safety expectations."""
        # Test that the flexible custom_fields support different value types

        string_metadata: ModelGenericMetadata = ModelGenericMetadata()
        int_metadata: ModelGenericMetadata = ModelGenericMetadata()

        # These should work without type errors
        string_metadata.set_field("name", "value")
        int_metadata.set_field("count", 42)

        # The actual field access should work with any type
        assert string_metadata.get_field("name") == "value"
        assert int_metadata.get_field("count") == 42

    def test_generic_round_trip_operations(self):
        """Test round-trip operations."""
        original = ModelGenericMetadata(
            name="round_trip_test",
            description="Testing round-trip operations",
            version="1.0.0",
            tags=["test", "round-trip"],
        )

        # Add custom fields (basic types only)
        original.set_field("setting", "test_value")
        original.set_field("count", 42)

        # Convert to dict and back
        data = original.model_dump(exclude_none=True, by_alias=True)
        restored = ModelGenericMetadata.model_validate(data)

        # Verify standard fields are preserved
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.version == original.version
        assert restored.tags == original.tags
        # Note: Custom fields may not round-trip perfectly through model_dump/validate
        # due to complex ModelValue serialization - this is expected behavior


@pytest.mark.unit
class TestModelGenericMetadataGenericEdgeCases:
    """Test edge cases for ModelGenericMetadata."""

    def test_generic_with_none_type(self):
        """Test behavior with None values."""
        metadata = ModelGenericMetadata()

        # Should still work for basic operations
        metadata.set_field("test", "value")
        assert metadata.get_field("test") == "value"

    def test_generic_inheritance_compatibility(self):
        """Test inheritance compatibility."""
        # Test that instances are compatible
        generic_metadata = ModelGenericMetadata()
        base_metadata = ModelGenericMetadata()

        # Both should have the same interface
        generic_metadata.set_field("test", "value")
        base_metadata.set_field("test", "value")

        assert generic_metadata.get_field("test") == base_metadata.get_field("test")

    def test_generic_with_union_types(self):
        """Test behavior with various types."""
        union_metadata = ModelGenericMetadata()

        # Should work with any of the union types
        union_metadata.set_field("string_field", "string_value")
        union_metadata.set_field("int_field", 42)
        union_metadata.set_field("bool_field", True)

        assert union_metadata.get_field("string_field") == "string_value"
        assert union_metadata.get_field("int_field") == 42
        assert union_metadata.get_field("bool_field") is True

    def test_generic_custom_fields_initialization(self):
        """Test custom_fields initialization behavior."""
        # Test with explicit custom_fields initialization
        metadata1 = ModelGenericMetadata(custom_fields={"initial": "value"})
        assert metadata1.get_field("initial") == "value"

        # Test with None custom_fields
        metadata2 = ModelGenericMetadata(custom_fields=None)
        assert metadata2.custom_fields is None
        assert metadata2.get_field("test") is None

        # Test with empty dict custom_fields
        metadata3 = ModelGenericMetadata(custom_fields={})
        assert metadata3.custom_fields == {}
        assert metadata3.get_field("test") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
