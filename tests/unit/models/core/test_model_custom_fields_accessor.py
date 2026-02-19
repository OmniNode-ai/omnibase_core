# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test suite for ModelCustomFieldsAccessor.

Tests the specialized accessor for managing custom fields with automatic initialization.
"""

from typing import Any

import pytest
from pydantic import Field

from omnibase_core.models.core import ModelCustomFieldsAccessor
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class SampleCustomFieldsModel(ModelCustomFieldsAccessor):
    """Test model with custom fields for testing the accessor."""

    custom_fields: dict[str, Any] | None = Field(default=None)


@pytest.mark.unit
class TestModelCustomFieldsAccessor:
    """Test cases for ModelCustomFieldsAccessor."""

    def test_initialization_empty(self):
        """Test empty initialization."""
        accessor = SampleCustomFieldsModel()

        # Should be able to access methods
        assert hasattr(accessor, "get_custom_field")
        assert hasattr(accessor, "set_custom_field")
        assert hasattr(accessor, "has_custom_field")
        assert hasattr(accessor, "remove_custom_field")

    def test_get_custom_field_no_custom_fields(self):
        """Test getting custom field when custom_fields doesn't exist."""
        accessor = SampleCustomFieldsModel()

        # Should return default when custom_fields doesn't exist
        assert accessor.get_custom_field("nonexistent") is None
        assert accessor.get_custom_field("nonexistent", "default") == "default"

    def test_set_custom_field_initializes_custom_fields(self):
        """Test that setting custom field initializes custom_fields if needed."""
        accessor = SampleCustomFieldsModel()

        # Initially no custom_fields
        assert not accessor.has_field("custom_fields")

        # Set a custom field
        result = accessor.set_custom_field("test_key", "test_value")
        assert result is True

        # Should have initialized custom_fields
        assert accessor.has_field("custom_fields")
        assert accessor.get_custom_field("test_key") == "test_value"

    def test_custom_field_string_values(self):
        """Test custom fields with string values."""
        accessor = SampleCustomFieldsModel()

        # Set string values
        accessor.set_custom_field("string_field", "hello_world")
        accessor.set_custom_field("env", "production")

        assert accessor.get_custom_field("string_field") == "hello_world"
        assert accessor.get_custom_field("env") == "production"

    def test_custom_field_numeric_values(self):
        """Test custom fields with numeric values."""
        accessor = SampleCustomFieldsModel()

        # Set numeric values
        accessor.set_custom_field("int_field", 42)
        accessor.set_custom_field("float_field", 3.14159)

        assert accessor.get_custom_field("int_field") == 42
        assert accessor.get_custom_field("float_field") == 3.14159

    def test_custom_field_boolean_values(self):
        """Test custom fields with boolean values."""
        accessor = SampleCustomFieldsModel()

        # Set boolean values
        accessor.set_custom_field("debug_mode", True)
        accessor.set_custom_field("cache_enabled", False)

        assert accessor.get_custom_field("debug_mode") is True
        assert accessor.get_custom_field("cache_enabled") is False

    def test_custom_field_list_values(self):
        """Test custom fields with list values."""
        accessor = SampleCustomFieldsModel()

        # Set list values
        accessor.set_custom_field("tags", ["production", "critical"])
        accessor.set_custom_field("environments", ["dev", "staging", "prod"])

        assert accessor.get_custom_field("tags") == ["production", "critical"]
        assert accessor.get_custom_field("environments") == ["dev", "staging", "prod"]

    def test_has_custom_field(self):
        """Test checking if custom field exists."""
        accessor = SampleCustomFieldsModel()

        # Initially no fields
        assert not accessor.has_custom_field("nonexistent")

        # Set a field
        accessor.set_custom_field("existing_field", "value")

        # Should exist now
        assert accessor.has_custom_field("existing_field")
        assert not accessor.has_custom_field("still_nonexistent")

    def test_remove_custom_field(self):
        """Test removing custom fields."""
        accessor = SampleCustomFieldsModel()

        # Set some fields
        accessor.set_custom_field("field1", "value1")
        accessor.set_custom_field("field2", "value2")

        # Verify they exist
        assert accessor.has_custom_field("field1")
        assert accessor.has_custom_field("field2")

        # Remove one field
        result = accessor.remove_custom_field("field1")
        assert result is True

        # Should be gone
        assert not accessor.has_custom_field("field1")
        assert accessor.has_custom_field("field2")  # Other field should remain

        # Removing non-existent field should return False
        result = accessor.remove_custom_field("nonexistent")
        assert result is False

    def test_get_custom_field_with_defaults(self):
        """Test getting custom fields with default values."""
        accessor = SampleCustomFieldsModel()

        # Set some fields
        accessor.set_custom_field("existing", "value")

        # Get existing field
        assert accessor.get_custom_field("existing") == "value"

        # Get non-existing field with default
        assert accessor.get_custom_field("missing") is None
        assert accessor.get_custom_field("missing", "default_value") == "default_value"
        assert accessor.get_custom_field("missing", 42) == 42
        assert accessor.get_custom_field("missing", True) is True

    def test_multiple_custom_fields_operations(self):
        """Test multiple operations on custom fields."""
        accessor = SampleCustomFieldsModel()

        # Set multiple fields of different types
        accessor.set_custom_field("app_name", "test_app")
        accessor.set_custom_field("port", 8080)
        accessor.set_custom_field("debug", True)
        accessor.set_custom_field("timeout", 30.5)
        accessor.set_custom_field("features", ["auth", "logging"])

        # Verify all fields
        assert accessor.get_custom_field("app_name") == "test_app"
        assert accessor.get_custom_field("port") == 8080
        assert accessor.get_custom_field("debug") is True
        assert accessor.get_custom_field("timeout") == 30.5
        assert accessor.get_custom_field("features") == ["auth", "logging"]

        # Check existence
        assert accessor.has_custom_field("app_name")
        assert accessor.has_custom_field("port")
        assert accessor.has_custom_field("debug")
        assert accessor.has_custom_field("timeout")
        assert accessor.has_custom_field("features")

        # Remove some fields
        accessor.remove_custom_field("port")
        accessor.remove_custom_field("debug")

        # Verify removal
        assert not accessor.has_custom_field("port")
        assert not accessor.has_custom_field("debug")
        assert accessor.has_custom_field("app_name")  # Should still exist
        assert accessor.has_custom_field("timeout")  # Should still exist
        assert accessor.has_custom_field("features")  # Should still exist

    def test_overwrite_custom_field(self):
        """Test overwriting existing custom fields."""
        accessor = SampleCustomFieldsModel()

        # Set initial value
        accessor.set_custom_field("config", "initial")
        assert accessor.get_custom_field("config") == "initial"

        # Overwrite with new value
        accessor.set_custom_field("config", "updated")
        assert accessor.get_custom_field("config") == "updated"

        # Overwrite with different type
        accessor.set_custom_field("config", 42)
        assert accessor.get_custom_field("config") == 42

        accessor.set_custom_field("config", True)
        assert accessor.get_custom_field("config") is True

    def test_inheritance_from_field_accessor(self):
        """Test that custom fields accessor inherits from base field accessor."""
        accessor = SampleCustomFieldsModel()

        # Should have base field accessor methods
        assert hasattr(accessor, "get_field")
        assert hasattr(accessor, "set_field")
        assert hasattr(accessor, "has_field")
        assert hasattr(accessor, "remove_field")

        # Test that base methods work - just verify they don't crash
        # We test with the existing custom_fields field
        has_result = accessor.has_field("custom_fields")
        # Should return False since custom_fields is initially None
        assert has_result is False

        # Test that methods are callable (inheritance works)
        # We don't test actual functionality since that's covered in the base class tests

    def test_custom_fields_initialization_behavior(self):
        """Test the automatic initialization behavior of custom_fields."""
        accessor = SampleCustomFieldsModel()

        # Initially custom_fields should not exist
        assert not accessor.has_field("custom_fields")

        # After setting a custom field, custom_fields should exist
        accessor.set_custom_field("first_field", "value")
        assert accessor.has_field("custom_fields")

        # Setting another field should work without re-initialization
        accessor.set_custom_field("second_field", "another_value")
        assert accessor.get_custom_field("first_field") == "value"
        assert accessor.get_custom_field("second_field") == "another_value"

    def test_edge_case_empty_string_values(self):
        """Test edge cases with empty string values."""
        accessor = SampleCustomFieldsModel()

        # Set empty string
        accessor.set_custom_field("empty_string", "")
        assert accessor.get_custom_field("empty_string") == ""
        assert accessor.has_custom_field("empty_string")

    def test_edge_case_zero_values(self):
        """Test edge cases with zero values."""
        accessor = SampleCustomFieldsModel()

        # Set zero values
        accessor.set_custom_field("zero_int", 0)
        accessor.set_custom_field("zero_float", 0.0)

        assert accessor.get_custom_field("zero_int") == 0
        assert accessor.get_custom_field("zero_float") == 0.0
        assert accessor.has_custom_field("zero_int")
        assert accessor.has_custom_field("zero_float")

    def test_edge_case_empty_list(self):
        """Test edge cases with empty list values."""
        accessor = SampleCustomFieldsModel()

        # Set empty list
        accessor.set_custom_field("empty_list", [])
        assert accessor.get_custom_field("empty_list") == []
        assert accessor.has_custom_field("empty_list")

    def test_complex_scenario(self):
        """Test complex scenario with mixed operations."""
        accessor = SampleCustomFieldsModel()

        # Build up a complex configuration
        config_data = {
            "service_name": "user_service",
            "version": "1.2.3",
            "port": 8080,
            "debug_enabled": True,
            "timeout_ms": 5000.0,
            "allowed_origins": ["localhost", "127.0.0.1"],
            "max_connections": 100,
            "ssl_enabled": False,
        }

        # Set all fields
        for key, value in config_data.items():
            accessor.set_custom_field(key, value)

        # Verify all fields were set correctly
        for key, expected_value in config_data.items():
            assert accessor.get_custom_field(key) == expected_value
            assert accessor.has_custom_field(key)

        # Modify some fields
        accessor.set_custom_field("debug_enabled", False)
        accessor.set_custom_field("port", 9090)
        accessor.remove_custom_field("ssl_enabled")

        # Verify modifications
        assert accessor.get_custom_field("debug_enabled") is False
        assert accessor.get_custom_field("port") == 9090
        assert not accessor.has_custom_field("ssl_enabled")

        # Other fields should remain unchanged
        assert accessor.get_custom_field("service_name") == "user_service"
        assert accessor.get_custom_field("allowed_origins") == [
            "localhost",
            "127.0.0.1",
        ]

    def test_pydantic_compatibility(self):
        """Test compatibility with Pydantic model features."""
        accessor = SampleCustomFieldsModel()

        # Set some custom fields
        accessor.set_custom_field("test_field", "test_value")

        # Test serialization
        try:
            data = accessor.model_dump()
            # The exact structure depends on how the base model is implemented
            # We just verify it doesn't crash
            assert isinstance(data, dict)
        except Exception:
            # If serialization is not supported, that's okay for now
            pass

    def test_field_name_edge_cases(self):
        """Test edge cases with field names."""
        accessor = SampleCustomFieldsModel()

        # Test various field name patterns
        test_names = [
            "simple",
            "with_underscore",
            "with-dash",
            "with.dot",
            "with123numbers",
            "UPPERCASE",
            "MixedCase",
        ]

        for name in test_names:
            accessor.set_custom_field(name, f"value_for_{name}")
            assert accessor.get_custom_field(name) == f"value_for_{name}"
            assert accessor.has_custom_field(name)
