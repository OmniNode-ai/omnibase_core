"""
Test suite for ModelCustomProperties.

Tests the generic custom properties pattern that replaces repetitive custom field patterns.
"""

import pytest

from omnibase_core.models.core import ModelCustomProperties


class TestModelCustomProperties:
    """Test cases for ModelCustomProperties."""

    def test_initialization_empty(self):
        """Test empty initialization."""
        props = ModelCustomProperties()

        assert props.custom_strings == {}
        assert props.custom_numbers == {}
        assert props.custom_flags == {}
        assert props.is_empty()
        assert props.get_field_count() == 0

    def test_set_custom_string(self):
        """Test setting custom string values."""
        props = ModelCustomProperties()

        props.set_custom_string("environment", "production")
        props.set_custom_string("region", "us-west-2")

        assert props.custom_strings["environment"] == "production"
        assert props.custom_strings["region"] == "us-west-2"
        assert not props.is_empty()
        assert props.get_field_count() == 2

    def test_set_custom_number(self):
        """Test setting custom numeric values."""
        props = ModelCustomProperties()

        props.set_custom_number("timeout", 30.5)
        props.set_custom_number("retry_count", 3.0)

        assert props.custom_numbers["timeout"] == 30.5
        assert props.custom_numbers["retry_count"] == 3.0
        assert props.get_field_count() == 2

    def test_set_custom_flag(self):
        """Test setting custom boolean values."""
        props = ModelCustomProperties()

        props.set_custom_flag("debug_mode", True)
        props.set_custom_flag("cache_enabled", False)

        assert props.custom_flags["debug_mode"] is True
        assert props.custom_flags["cache_enabled"] is False
        assert props.get_field_count() == 2

    def test_get_custom_value(self):
        """Test retrieving custom values by key."""
        props = ModelCustomProperties()

        props.set_custom_string("name", "test")
        props.set_custom_number("value", 42.0)
        props.set_custom_flag("enabled", True)

        assert props.get_custom_value("name") == "test"
        assert props.get_custom_value("value") == 42.0
        assert props.get_custom_value("enabled") is True
        assert props.get_custom_value("nonexistent") is None

    def test_has_custom_field(self):
        """Test checking for field existence."""
        props = ModelCustomProperties()

        props.set_custom_string("test", "value")

        assert props.has_custom_field("test")
        assert not props.has_custom_field("missing")

    def test_remove_custom_field(self):
        """Test removing custom fields."""
        props = ModelCustomProperties()

        props.set_custom_string("temp", "value")
        props.set_custom_number("count", 10.0)

        assert props.remove_custom_field("temp")
        assert not props.has_custom_field("temp")
        assert not props.remove_custom_field("nonexistent")
        assert props.has_custom_field("count")

    def test_get_all_custom_fields(self):
        """Test getting unified view of all custom fields."""
        props = ModelCustomProperties()

        props.set_custom_string("name", "test")
        props.set_custom_number("value", 42.0)
        props.set_custom_flag("enabled", True)

        all_fields = props.get_all_custom_fields()

        assert all_fields == {
            "name": "test",
            "value": 42.0,
            "enabled": True,
        }

    def test_set_custom_value_auto_type(self):
        """Test automatic type detection for custom values."""
        props = ModelCustomProperties()

        props.set_custom_value("string_val", "hello")
        props.set_custom_value("int_val", 42)
        props.set_custom_value("float_val", 3.14)
        props.set_custom_value("bool_val", True)

        assert props.custom_strings["string_val"] == "hello"
        assert props.custom_numbers["int_val"] == 42.0
        assert props.custom_numbers["float_val"] == 3.14
        assert props.custom_flags["bool_val"] is True

    def test_set_custom_value_invalid_type(self):
        """Test error handling for unsupported types."""
        props = ModelCustomProperties()

        with pytest.raises(TypeError, match="Unsupported custom value type"):
            props.set_custom_value("invalid", [1, 2, 3])

    def test_update_from_dict(self):
        """Test updating from dictionary with mixed types."""
        props = ModelCustomProperties()

        data = {
            "environment": "staging",
            "timeout": 45.0,
            "retries": 5,
            "debug": True,
            "invalid": None,  # Should be skipped
        }

        props.update_from_dict(data)

        assert props.custom_strings["environment"] == "staging"
        assert props.custom_numbers["timeout"] == 45.0
        assert props.custom_numbers["retries"] == 5.0
        assert props.custom_flags["debug"] is True
        assert not props.has_custom_field("invalid")

    def test_clear_all(self):
        """Test clearing all custom properties."""
        props = ModelCustomProperties()

        props.set_custom_string("test", "value")
        props.set_custom_number("count", 5.0)
        props.set_custom_flag("flag", True)

        assert not props.is_empty()

        props.clear_all()

        assert props.is_empty()
        assert props.get_field_count() == 0

    def test_from_dict_class_method(self):
        """Test creating instance from dictionary."""
        data = {
            "name": "service",
            "timeout": 30.0,
            "enabled": True,
        }

        props = ModelCustomProperties.from_dict(data)

        assert props.custom_strings["name"] == "service"
        assert props.custom_numbers["timeout"] == 30.0
        assert props.custom_flags["enabled"] is True

    def test_from_metadata(self):
        """Test creating from metadata format."""
        metadata_data = {
            "service_name": "test-service",
            "timeout": 60.0,
            "retry_count": 3,
            "debug_enabled": True,
        }

        props = ModelCustomProperties.from_metadata(metadata_data)

        assert props.custom_strings["service_name"] == "test-service"
        assert props.custom_numbers["timeout"] == 60.0
        assert props.custom_numbers["retry_count"] == 3.0
        assert props.custom_flags["debug_enabled"] is True

    def test_to_metadata(self):
        """Test converting to metadata format."""
        props = ModelCustomProperties()

        props.set_custom_string("env", "prod")
        props.set_custom_number("limit", 100.0)
        props.set_custom_flag("strict", True)

        metadata = props.to_metadata()

        assert metadata == {
            "env": "prod",
            "limit": 100.0,
            "strict": True,
        }

    def test_metadata_round_trip(self):
        """Test round-trip conversion with metadata format."""
        original_metadata = {
            "database": "users",
            "pool_size": 10.0,
            "ssl_enabled": True,
        }

        # Convert to properties format
        props = ModelCustomProperties.from_metadata(original_metadata)

        # Convert back to metadata format
        converted_metadata = props.to_metadata()

        assert converted_metadata == original_metadata

    def test_mixed_operations(self):
        """Test complex usage with mixed operations."""
        props = ModelCustomProperties()

        # Add some initial values
        props.update_from_dict(
            {
                "service": "api",
                "version": 1.2,
                "active": True,
            },
        )

        # Modify individual values
        props.set_custom_string("service", "updated-api")
        props.remove_custom_field("version")
        props.set_custom_number("timeout", 45.0)

        # Verify final state
        assert props.custom_strings["service"] == "updated-api"
        assert not props.has_custom_field("version")
        assert props.custom_numbers["timeout"] == 45.0
        assert props.custom_flags["active"] is True
        assert props.get_field_count() == 3

    def test_pydantic_validation(self):
        """Test Pydantic validation and serialization."""
        props = ModelCustomProperties(
            custom_strings={"env": "test"},
            custom_numbers={"timeout": 30.0},
            custom_flags={"debug": True},
        )

        # Test serialization
        data = props.model_dump()

        assert data["custom_strings"] == {"env": "test"}
        assert data["custom_numbers"] == {"timeout": 30.0}
        assert data["custom_flags"] == {"debug": True}

        # Test deserialization
        new_props = ModelCustomProperties.model_validate(data)

        assert new_props.custom_strings == props.custom_strings
        assert new_props.custom_numbers == props.custom_numbers
        assert new_props.custom_flags == props.custom_flags
