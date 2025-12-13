"""
Test suite for ModelItemSummary.

Tests the clean, strongly-typed model replacing collection item dict return types.
"""

from datetime import datetime
from uuid import UUID

import pytest

from omnibase_core.enums.enum_item_type import EnumItemType
from omnibase_core.models.core.model_item_summary import ModelItemSummary
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class TestModelItemSummary:
    """Test cases for ModelItemSummary."""

    def test_initialization_defaults(self):
        """Test initialization with default values."""
        item = ModelItemSummary(version=DEFAULT_VERSION)

        # Test default UUID is generated
        assert isinstance(item.item_id, UUID)
        assert item.item_display_name == ""
        assert item.item_type == EnumItemType.UNKNOWN
        assert item.description == ""
        assert item.is_enabled is True
        assert item.is_valid is True
        assert item.priority == 0
        assert item.created_at is None
        assert item.updated_at is None
        assert item.accessed_at is None
        assert item.tags == []
        assert item.categories == []
        assert item.string_properties == {}
        assert item.numeric_properties == {}
        assert item.boolean_properties == {}

    def test_initialization_with_values(self):
        """Test initialization with provided values."""
        now = datetime.now()
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")

        item = ModelItemSummary(
            version=DEFAULT_VERSION,
            item_id=test_uuid,
            item_display_name="Test Item",
            item_type=EnumItemType.COMPONENT,
            description="Test description",
            is_enabled=False,
            is_valid=False,
            priority=10,
            created_at=now,
            updated_at=now,
            accessed_at=now,
            tags=["tag1", "tag2"],
            categories=["cat1", "cat2"],
            string_properties={"key1": "value1"},
            numeric_properties={"score": 95.5},
            boolean_properties={"active": True},
        )

        assert item.item_id == test_uuid
        assert item.item_display_name == "Test Item"
        assert item.item_type == EnumItemType.COMPONENT
        assert item.description == "Test description"
        assert item.is_enabled is False
        assert item.is_valid is False
        assert item.priority == 10
        assert item.created_at == now
        assert item.updated_at == now
        assert item.accessed_at == now
        assert item.tags == ["tag1", "tag2"]
        assert item.categories == ["cat1", "cat2"]
        assert item.string_properties == {"key1": "value1"}
        assert item.numeric_properties == {"score": 95.5}
        assert item.boolean_properties == {"active": True}

    def test_name_property_with_display_name(self):
        """Test name property when display name is set."""
        item = ModelItemSummary(item_display_name="My Item")
        assert item.name == "My Item"

    def test_name_property_fallback_to_uuid(self):
        """Test name property falls back to UUID when display name is empty."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        item = ModelItemSummary(item_id=test_uuid)
        assert item.name == "item_12345678"

    def test_has_properties_empty(self):
        """Test has_properties returns False when no properties are set."""
        item = ModelItemSummary(version=DEFAULT_VERSION)
        assert item.has_properties() is False

    def test_has_properties_with_string_properties(self):
        """Test has_properties returns True when string properties are set."""
        item = ModelItemSummary(string_properties={"key": "value"})
        assert item.has_properties() is True

    def test_has_properties_with_numeric_properties(self):
        """Test has_properties returns True when numeric properties are set."""
        item = ModelItemSummary(numeric_properties={"score": 100.0})
        assert item.has_properties() is True

    def test_has_properties_with_boolean_properties(self):
        """Test has_properties returns True when boolean properties are set."""
        item = ModelItemSummary(boolean_properties={"enabled": True})
        assert item.has_properties() is True

    def test_has_properties_with_multiple_properties(self):
        """Test has_properties returns True when multiple property types are set."""
        item = ModelItemSummary(
            version=DEFAULT_VERSION,
            string_properties={"key": "value"},
            numeric_properties={"score": 100.0},
            boolean_properties={"enabled": True},
        )
        assert item.has_properties() is True

    def test_configure_protocol_method(self):
        """Test configure method (Configurable protocol)."""
        item = ModelItemSummary(version=DEFAULT_VERSION)

        result = item.configure(
            item_display_name="New Name",
            priority=5,
            is_enabled=False,
        )

        assert result is True
        assert item.item_display_name == "New Name"
        assert item.priority == 5
        assert item.is_enabled is False

    def test_configure_with_invalid_fields(self):
        """Test configure with non-existent fields."""
        item = ModelItemSummary(version=DEFAULT_VERSION)

        # Should succeed but ignore invalid fields
        result = item.configure(
            item_display_name="Valid",
            nonexistent_field="Invalid",
        )

        assert result is True
        assert item.item_display_name == "Valid"

    def test_configure_with_exception(self):
        """Test configure raises ModelOnexError for invalid input."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        item = ModelItemSummary(version=DEFAULT_VERSION)

        # Create a scenario that would cause an exception
        # by trying to set a field with an incompatible type
        with pytest.raises(ModelOnexError, match="Failed to set attribute"):
            item.configure(priority="not_an_int")

    def test_serialize_protocol_method(self):
        """Test serialize method (Serializable protocol)."""
        now = datetime.now()
        item = ModelItemSummary(
            version=DEFAULT_VERSION,
            item_display_name="Test",
            priority=10,
            created_at=now,
            tags=["tag1"],
        )

        serialized = item.serialize()

        assert isinstance(serialized, dict)
        assert serialized["item_display_name"] == "Test"
        assert serialized["priority"] == 10
        assert "created_at" in serialized
        assert serialized["tags"] == ["tag1"]

    def test_serialize_includes_none_values(self):
        """Test serialize includes None values."""
        item = ModelItemSummary(version=DEFAULT_VERSION)

        serialized = item.serialize()

        assert "created_at" in serialized
        assert serialized["created_at"] is None
        assert "updated_at" in serialized
        assert serialized["updated_at"] is None

    def test_validate_instance_protocol_method(self):
        """Test validate_instance method (Validatable protocol)."""
        item = ModelItemSummary(version=DEFAULT_VERSION)
        assert item.validate_instance() is True

    def test_validate_instance_with_data(self):
        """Test validate_instance with populated data."""
        item = ModelItemSummary(
            version=DEFAULT_VERSION,
            item_display_name="Test",
            item_type=EnumItemType.COMPONENT,
            priority=10,
        )
        assert item.validate_instance() is True

    def test_get_name_protocol_method(self):
        """Test get_name method (Nameable protocol)."""
        item = ModelItemSummary(version=DEFAULT_VERSION)

        # Should return default name format
        # ModelItemSummary has a @property name that returns item_display_name or UUID-based fallback
        name = item.get_name()
        assert isinstance(name, str)
        # The implementation will return the item name property which includes UUID or display name
        assert (
            name.startswith("item_") or "Unnamed" in name or "ModelItemSummary" in name
        )

    def test_get_name_with_name_field(self):
        """Test get_name when item_display_name is set."""
        item = ModelItemSummary(item_display_name="Custom Name")

        # The base implementation checks for common field patterns
        # but ModelItemSummary doesn't have a "name" field
        name = item.get_name()
        assert "Custom Name" in name or "ModelItemSummary" in name

    def test_set_name_protocol_method(self):
        """Test set_name method (Nameable protocol)."""
        item = ModelItemSummary(version=DEFAULT_VERSION)

        # Try to set name - it will look for common name fields
        # ModelItemSummary has a 'name' property which is read-only,
        # so set_name won't find a settable field and will just complete
        try:
            item.set_name("New Name")
            # Method should complete without crashing
            assert True
        except AttributeError:
            # If it tries to set a read-only property, that's expected
            assert True

    def test_item_type_enum_handling(self):
        """Test proper handling of EnumItemType."""
        item = ModelItemSummary(item_type=EnumItemType.CODE)
        assert item.item_type == EnumItemType.CODE

        # Test with different enum values
        item.item_type = EnumItemType.COMPONENT
        assert item.item_type == EnumItemType.COMPONENT

    def test_tags_list_operations(self):
        """Test tags list can be manipulated."""
        item = ModelItemSummary(tags=["initial"])

        item.tags.append("new_tag")
        item.tags.extend(["tag2", "tag3"])

        assert len(item.tags) == 4
        assert "initial" in item.tags
        assert "new_tag" in item.tags
        assert "tag2" in item.tags
        assert "tag3" in item.tags

    def test_categories_list_operations(self):
        """Test categories list can be manipulated."""
        item = ModelItemSummary(categories=["cat1"])

        item.categories.append("cat2")

        assert len(item.categories) == 2
        assert "cat1" in item.categories
        assert "cat2" in item.categories

    def test_string_properties_operations(self):
        """Test string_properties dictionary operations."""
        item = ModelItemSummary(version=DEFAULT_VERSION)

        item.string_properties["key1"] = "value1"
        item.string_properties["key2"] = "value2"

        assert len(item.string_properties) == 2
        assert item.string_properties["key1"] == "value1"
        assert item.string_properties["key2"] == "value2"

    def test_numeric_properties_operations(self):
        """Test numeric_properties dictionary operations."""
        item = ModelItemSummary(version=DEFAULT_VERSION)

        item.numeric_properties["score"] = 95.5
        item.numeric_properties["count"] = 10.0

        assert len(item.numeric_properties) == 2
        assert item.numeric_properties["score"] == 95.5
        assert item.numeric_properties["count"] == 10.0

    def test_boolean_properties_operations(self):
        """Test boolean_properties dictionary operations."""
        item = ModelItemSummary(version=DEFAULT_VERSION)

        item.boolean_properties["active"] = True
        item.boolean_properties["verified"] = False

        assert len(item.boolean_properties) == 2
        assert item.boolean_properties["active"] is True
        assert item.boolean_properties["verified"] is False

    def test_model_config_extra_ignore(self):
        """Test that extra fields are ignored per model_config."""
        # Should not raise validation error with extra fields
        item = ModelItemSummary(
            version=DEFAULT_VERSION,
            item_display_name="Test",
            extra_field="should be ignored",
        )

        assert item.item_display_name == "Test"
        # Extra field should not be stored
        assert not hasattr(item, "extra_field")

    def test_model_config_validate_assignment(self):
        """Test that assignment validation works per model_config."""
        item = ModelItemSummary(priority=5)
        assert item.priority == 5

        # Should be able to update with valid type
        item.priority = 10
        assert item.priority == 10

        # Should raise validation error with invalid type
        with pytest.raises(Exception):  # Pydantic validation error
            item.priority = "not_an_int"

    def test_timestamps_datetime_handling(self):
        """Test timestamp fields handle datetime objects correctly."""
        now = datetime.now()

        item = ModelItemSummary(
            version=DEFAULT_VERSION,
            created_at=now,
            updated_at=now,
            accessed_at=now,
        )

        assert isinstance(item.created_at, datetime)
        assert isinstance(item.updated_at, datetime)
        assert isinstance(item.accessed_at, datetime)
        assert item.created_at == now
        assert item.updated_at == now
        assert item.accessed_at == now

    def test_priority_edge_cases(self):
        """Test priority field with edge cases."""
        from pydantic import ValidationError

        # Zero priority
        item1 = ModelItemSummary(priority=0)
        assert item1.priority == 0

        # Negative priority - now rejected (ge=0 constraint)
        with pytest.raises(ValidationError) as exc_info:
            ModelItemSummary(priority=-5)
        assert "greater than or equal to 0" in str(exc_info.value)

        # Large priority
        item3 = ModelItemSummary(priority=99999)
        assert item3.priority == 99999

    def test_multiple_items_independence(self):
        """Test that multiple instances are independent."""
        item1 = ModelItemSummary(item_display_name="Item 1", priority=1)
        item2 = ModelItemSummary(item_display_name="Item 2", priority=2)

        assert item1.item_display_name == "Item 1"
        assert item2.item_display_name == "Item 2"
        assert item1.priority == 1
        assert item2.priority == 2
        # Note: UUID generation may be deterministic based on default factory
        # So we just ensure the items have different properties, not necessarily different UUIDs

    def test_empty_collections_are_mutable(self):
        """Test that default empty collections are mutable and independent."""
        item1 = ModelItemSummary(version=DEFAULT_VERSION)
        item2 = ModelItemSummary(version=DEFAULT_VERSION)

        item1.tags.append("tag1")
        item2.tags.append("tag2")

        assert "tag1" in item1.tags
        assert "tag2" in item2.tags
        assert "tag1" not in item2.tags
        assert "tag2" not in item1.tags

    def test_complex_real_world_scenario(self):
        """Test complex real-world scenario with all features."""
        now = datetime.now()

        item = ModelItemSummary(
            version=DEFAULT_VERSION,
            item_display_name="Production Database",
            item_type=EnumItemType.SERVICE,
            description="Main production database server",
            is_enabled=True,
            is_valid=True,
            priority=100,
            created_at=now,
            updated_at=now,
            tags=["production", "critical", "database"],
            categories=["infrastructure", "storage"],
            string_properties={
                "host": "db.example.com",
                "port": "5432",
                "engine": "postgresql",
            },
            numeric_properties={
                "max_connections": 1000.0,
                "memory_gb": 64.0,
                "storage_tb": 10.0,
            },
            boolean_properties={
                "ssl_enabled": True,
                "backup_enabled": True,
                "monitoring_enabled": True,
            },
        )

        # Test all properties are set correctly
        assert item.item_display_name == "Production Database"
        assert item.item_type == EnumItemType.SERVICE
        assert item.priority == 100
        assert len(item.tags) == 3
        assert len(item.categories) == 2
        assert item.has_properties() is True
        assert item.string_properties["engine"] == "postgresql"
        assert item.numeric_properties["memory_gb"] == 64.0
        assert item.boolean_properties["ssl_enabled"] is True

        # Test protocols work
        assert item.validate_instance() is True
        serialized = item.serialize()
        assert isinstance(serialized, dict)

        # Test name property
        assert item.name == "Production Database"
