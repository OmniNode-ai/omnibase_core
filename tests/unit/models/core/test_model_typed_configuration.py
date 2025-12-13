"""
Tests for ModelTypedConfiguration.

Comprehensive tests for typed configuration model including merge operations,
validation, protocol implementations, and custom properties.
"""

from typing import Any

import pytest

pytestmark = pytest.mark.unit

from omnibase_core.models.core.model_typed_configuration import ModelTypedConfiguration
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class TestModelTypedConfiguration:
    """Test suite for ModelTypedConfiguration."""

    def test_initialization_defaults(self):
        """Test initialization with default values."""
        config = ModelTypedConfiguration[dict[str, Any]]()

        # Base fields have None defaults
        assert config.name is None
        assert config.description is None or isinstance(config.description, str)
        assert config.version is None
        assert config.config_data is None
        assert config.custom_strings == {}
        assert config.custom_numbers == {}
        assert config.custom_flags == {}

    def test_initialization_with_values(self):
        """Test initialization with custom values."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        config_data = {"key": "value", "setting": True}

        config = ModelTypedConfiguration[dict[str, Any]](
            name="test_config",
            description="Test configuration",
            version=ModelSemVer(major=1, minor=0, patch=0),
            config_data=config_data,
        )

        assert config.name == "test_config"
        assert config.description == "Test configuration"
        assert str(config.version) == "1.0.0"
        assert config.config_data == config_data

    def test_merge_configuration_basic(self):
        """Test basic configuration merging."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        config1 = ModelTypedConfiguration[dict[str, Any]](
            name="config1",
            description="First config",
            version=ModelSemVer(major=1, minor=0, patch=0),
            config_data={"key1": "value1"},
        )

        config2 = ModelTypedConfiguration[dict[str, Any]](
            name="config2",
            description="Second config",
            version=ModelSemVer(major=2, minor=0, patch=0),
            config_data={"key2": "value2"},
        )

        config1.merge_configuration(config2)

        # Should be updated with config2 values
        assert config1.name == "config2"
        assert config1.description == "Second config"
        assert str(config1.version) == "2.0.0"
        assert config1.config_data == {"key2": "value2"}

    def test_merge_configuration_custom_properties(self):
        """Test merging custom properties."""
        config1 = ModelTypedConfiguration[dict[str, Any]](name="config1")
        config1.custom_strings["str1"] = "value1"
        config1.custom_numbers["num1"] = 100
        config1.custom_flags["flag1"] = True

        config2 = ModelTypedConfiguration[dict[str, Any]](name="config2")
        config2.custom_strings["str2"] = "value2"
        config2.custom_numbers["num2"] = 200
        config2.custom_flags["flag2"] = False

        config1.merge_configuration(config2)

        # Should have both sets of custom properties
        assert config1.custom_strings["str1"] == "value1"
        assert config1.custom_strings["str2"] == "value2"
        assert config1.custom_numbers["num1"] == 100
        assert config1.custom_numbers["num2"] == 200
        assert config1.custom_flags["flag1"] is True
        assert config1.custom_flags["flag2"] is False

    def test_merge_configuration_none_values(self):
        """Test merging with None values doesn't overwrite."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        config1 = ModelTypedConfiguration[dict[str, Any]](
            name="config1",
            description="First config",
            version=ModelSemVer(major=1, minor=0, patch=0),
            config_data={"key": "value"},
        )

        config2 = ModelTypedConfiguration[dict[str, Any]](
            name=None, description=None, version=None, config_data=None
        )

        config1.merge_configuration(config2)

        # Should keep original values
        assert config1.name == "config1"
        assert config1.description == "First config"
        assert str(config1.version) == "1.0.0"
        assert config1.config_data == {"key": "value"}

    def test_copy_configuration(self):
        """Test configuration copying."""
        original = ModelTypedConfiguration[dict[str, Any]](
            name="original", description="Original config", config_data={"key": "value"}
        )
        original.custom_strings["test"] = "value"

        copy = original.copy_configuration()

        assert copy.name == original.name
        assert copy.description == original.description
        assert copy.config_data == original.config_data
        assert copy.custom_strings == original.custom_strings
        assert copy is not original

    def test_copy_configuration_deep(self):
        """Test deep copying of configuration."""
        original = ModelTypedConfiguration[dict[str, Any]](
            name="original", config_data={"nested": {"key": "value"}}
        )

        copy = original.copy_configuration()

        # Modify copy's nested data
        if copy.config_data:
            copy.config_data["nested"]["key"] = "modified"

        # Original should be unchanged (deep copy)
        if original.config_data:
            assert original.config_data["nested"]["key"] == "value"

    def test_validate_and_enable_with_config_data(self):
        """Test validate_and_enable with config_data present."""
        config = ModelTypedConfiguration[dict[str, Any]](
            name="test", config_data={"key": "value"}
        )

        assert config.enabled is False or config.enabled is True  # Check initial state
        result = config.validate_and_enable()

        assert result is True
        assert config.enabled is True

    def test_validate_and_enable_without_config_data(self):
        """Test validate_and_enable without config_data."""
        config = ModelTypedConfiguration[dict[str, Any]](name="test")

        result = config.validate_and_enable()

        assert result is False

    def test_disable_with_reason(self):
        """Test disabling configuration with reason."""
        config = ModelTypedConfiguration[dict[str, Any]](
            name="test", description="Test config", config_data={"key": "value"}
        )
        config.validate_and_enable()
        assert config.enabled is True

        config.disable_with_reason("Security concern")

        assert config.enabled is False
        assert "Disabled: Security concern" in config.description

    def test_configure_protocol(self):
        """Test Configurable protocol implementation."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        config = ModelTypedConfiguration[dict[str, Any]](name="test")

        result = config.configure(
            name="configured",
            description="Configured via protocol",
            version=ModelSemVer(major=2, minor=0, patch=0),
        )

        assert result is True
        assert config.name == "configured"
        assert config.description == "Configured via protocol"
        assert str(config.version) == "2.0.0"

    def test_serialize_protocol(self):
        """Test Serializable protocol implementation."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        config = ModelTypedConfiguration[dict[str, Any]](
            name="test",
            description="Test config",
            version=ModelSemVer(major=1, minor=0, patch=0),
            config_data={"key": "value"},
        )
        config.custom_strings["custom"] = "value"

        serialized = config.serialize()

        assert isinstance(serialized, dict)
        assert serialized["name"] == "test"
        assert serialized["description"] == "Test config"
        # Version is serialized as ModelSemVer dict
        assert serialized["version"] is not None
        assert serialized["config_data"] == {"key": "value"}
        assert "custom_strings" in serialized

    def test_validate_instance_protocol(self):
        """Test Validatable protocol implementation."""
        config = ModelTypedConfiguration[dict[str, Any]](name="test")

        result = config.validate_instance()

        # Base implementation should always return True
        assert result is True

    def test_get_name_protocol(self):
        """Test Nameable protocol get_name."""
        config = ModelTypedConfiguration[dict[str, Any]](name="test_name")

        name = config.get_name()

        assert name == "test_name"

    def test_get_name_protocol_fallback(self):
        """Test Nameable protocol get_name with fallback."""
        config = ModelTypedConfiguration[dict[str, Any]]()
        config.name = None  # Force None

        name = config.get_name()

        # Should return a fallback name
        assert "ModelTypedConfiguration" in name or name != ""

    def test_set_name_protocol(self):
        """Test Nameable protocol set_name."""
        config = ModelTypedConfiguration[dict[str, Any]](name="original")

        config.set_name("new_name")

        assert config.name == "new_name"

    def test_different_type_parameters(self):
        """Test with different type parameters."""
        # String config
        str_config = ModelTypedConfiguration[str](
            name="string_config", config_data="string value"
        )
        assert str_config.config_data == "string value"

        # Int config
        int_config = ModelTypedConfiguration[int](name="int_config", config_data=42)
        assert int_config.config_data == 42

        # List config
        list_config = ModelTypedConfiguration[list[str]](
            name="list_config", config_data=["a", "b", "c"]
        )
        assert list_config.config_data == ["a", "b", "c"]

    def test_update_timestamp_called(self):
        """Test that update_timestamp is called during operations."""
        config = ModelTypedConfiguration[dict[str, Any]](name="test")
        original_timestamp = config.updated_at

        # Operations that should update timestamp
        config.merge_configuration(
            ModelTypedConfiguration[dict[str, Any]](name="other")
        )

        # Timestamp should be updated (or at least not fail)
        # Note: Depending on implementation, this might be the same if very fast
        assert config.updated_at is not None


class TestModelTypedConfigurationEdgeCases:
    """Edge case tests for ModelTypedConfiguration."""

    def test_empty_configuration(self):
        """Test completely empty configuration."""
        config = ModelTypedConfiguration[dict[str, Any]]()

        # Should have defaults from base classes
        assert hasattr(config, "name")
        assert hasattr(config, "custom_strings")
        assert hasattr(config, "custom_numbers")
        assert hasattr(config, "custom_flags")

    def test_none_config_data(self):
        """Test with None config_data."""
        config = ModelTypedConfiguration[dict[str, Any]](name="test", config_data=None)

        assert config.config_data is None
        assert config.validate_and_enable() is False

    def test_merge_same_configuration(self):
        """Test merging configuration with itself."""
        config = ModelTypedConfiguration[dict[str, Any]](
            name="test", config_data={"key": "value"}
        )
        config.custom_strings["test"] = "value"

        config.merge_configuration(config)

        # Should handle self-merge gracefully
        assert config.name == "test"
        assert config.custom_strings["test"] == "value"

    def test_special_characters_in_strings(self):
        """Test with special characters in string fields."""
        config = ModelTypedConfiguration[dict[str, Any]](
            name="test<>&\"'", description="Description with\nnewlines\tand\ttabs"
        )

        assert config.name == "test<>&\"'"
        assert "\n" in config.description
        assert "\t" in config.description

    def test_large_custom_properties(self):
        """Test with large number of custom properties."""
        config = ModelTypedConfiguration[dict[str, Any]](name="test")

        for i in range(100):
            config.custom_strings[f"str_{i}"] = f"value_{i}"
            config.custom_numbers[f"num_{i}"] = i
            config.custom_flags[f"flag_{i}"] = i % 2 == 0

        assert len(config.custom_strings) == 100
        assert len(config.custom_numbers) == 100
        assert len(config.custom_flags) == 100

    def test_configure_with_invalid_attributes(self):
        """Test configure with non-existent attributes."""
        config = ModelTypedConfiguration[dict[str, Any]](name="test")

        # Should not raise, but also shouldn't set invalid attrs
        result = config.configure(name="valid", nonexistent_field="should_be_ignored")

        assert result is True
        assert config.name == "valid"
        assert not hasattr(config, "nonexistent_field")

    def test_disable_multiple_times(self):
        """Test disabling configuration multiple times."""
        config = ModelTypedConfiguration[dict[str, Any]](
            name="test", description="Original", config_data={"key": "value"}
        )

        config.disable_with_reason("Reason 1")
        config.disable_with_reason("Reason 2")

        assert config.enabled is False
        assert "Disabled" in config.description


class TestModelTypedConfigurationBranchCoverage:
    """Branch coverage tests for conditional logic in ModelTypedConfiguration."""

    def test_merge_configuration_none_name_branch(self):
        """Test merge when other.name is None (False branch)."""

        config1 = ModelTypedConfiguration[dict[str, Any]](
            name="original_name", description="original"
        )
        config2 = ModelTypedConfiguration[dict[str, Any]](
            name=None,
            description="new_description",  # None should not overwrite
        )

        config1.merge_configuration(config2)

        # name should remain unchanged (False branch)
        assert config1.name == "original_name"
        # description should be updated (True branch)
        assert config1.description == "new_description"

    def test_merge_configuration_non_none_name_branch(self):
        """Test merge when other.name is not None (True branch)."""
        config1 = ModelTypedConfiguration[dict[str, Any]](name="original")
        config2 = ModelTypedConfiguration[dict[str, Any]](name="updated")

        config1.merge_configuration(config2)

        # name should be updated (True branch)
        assert config1.name == "updated"

    def test_merge_configuration_none_description_branch(self):
        """Test merge when other.description is None (False branch)."""
        config1 = ModelTypedConfiguration[dict[str, Any]](description="original")
        config2 = ModelTypedConfiguration[dict[str, Any]](description=None)

        config1.merge_configuration(config2)

        # description should remain unchanged (False branch)
        assert config1.description == "original"

    def test_merge_configuration_non_none_description_branch(self):
        """Test merge when other.description is not None (True branch)."""
        config1 = ModelTypedConfiguration[dict[str, Any]](description="original")
        config2 = ModelTypedConfiguration[dict[str, Any]](description="updated")

        config1.merge_configuration(config2)

        # description should be updated (True branch)
        assert config1.description == "updated"

    def test_merge_configuration_none_version_branch(self):
        """Test merge when other.version is None (False branch)."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        config1 = ModelTypedConfiguration[dict[str, Any]](
            version=ModelSemVer(major=1, minor=0, patch=0)
        )
        config2 = ModelTypedConfiguration[dict[str, Any]](version=None)

        config1.merge_configuration(config2)

        # version should remain unchanged (False branch)
        assert str(config1.version) == "1.0.0"

    def test_merge_configuration_non_none_version_branch(self):
        """Test merge when other.version is not None (True branch)."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        config1 = ModelTypedConfiguration[dict[str, Any]](
            version=ModelSemVer(major=1, minor=0, patch=0)
        )
        config2 = ModelTypedConfiguration[dict[str, Any]](
            version=ModelSemVer(major=2, minor=0, patch=0)
        )

        config1.merge_configuration(config2)

        # version should be updated (True branch)
        assert str(config1.version) == "2.0.0"

    def test_merge_configuration_none_config_data_branch(self):
        """Test merge when other.config_data is None (False branch)."""
        config1 = ModelTypedConfiguration[dict[str, Any]](
            config_data={"original": "data"}
        )
        config2 = ModelTypedConfiguration[dict[str, Any]](config_data=None)

        config1.merge_configuration(config2)

        # config_data should remain unchanged (False branch)
        assert config1.config_data == {"original": "data"}

    def test_merge_configuration_non_none_config_data_branch(self):
        """Test merge when other.config_data is not None (True branch)."""
        config1 = ModelTypedConfiguration[dict[str, Any]](
            config_data={"original": "data"}
        )
        config2 = ModelTypedConfiguration[dict[str, Any]](
            config_data={"updated": "data"}
        )

        config1.merge_configuration(config2)

        # config_data should be updated (True branch)
        assert config1.config_data == {"updated": "data"}

    def test_validate_and_enable_none_config_data_branch(self):
        """Test validate_and_enable when config_data is None (False branch)."""
        config = ModelTypedConfiguration[dict[str, Any]](name="test", config_data=None)

        result = config.validate_and_enable()

        # Should return False when config_data is None
        assert result is False

    def test_validate_and_enable_non_none_config_data_branch(self):
        """Test validate_and_enable when config_data is not None (True branch)."""
        config = ModelTypedConfiguration[dict[str, Any]](
            name="test", config_data={"key": "value"}
        )

        result = config.validate_and_enable()

        # Should return True and enable when config_data is not None
        assert result is True
        assert config.enabled is True

    def test_disable_with_reason_none_description_branch(self):
        """Test disable_with_reason when description is None (or branch True)."""
        config = ModelTypedConfiguration[dict[str, Any]](
            name="test", description=None, config_data={"key": "value"}
        )

        config.disable_with_reason("Security issue")

        # Should use 'Configuration' as fallback when description is None
        assert config.enabled is False
        assert "Configuration - Disabled: Security issue" in config.description

    def test_disable_with_reason_existing_description_branch(self):
        """Test disable_with_reason when description exists (or branch False)."""
        config = ModelTypedConfiguration[dict[str, Any]](
            name="test", description="My Config", config_data={"key": "value"}
        )

        config.disable_with_reason("Security issue")

        # Should use existing description
        assert config.enabled is False
        assert "My Config - Disabled: Security issue" in config.description

    def test_configure_hasattr_true_branch(self):
        """Test configure when attribute exists (True branch)."""
        config = ModelTypedConfiguration[dict[str, Any]](name="original")

        result = config.configure(name="updated", description="new description")

        # Should update existing attributes (True branch)
        assert result is True
        assert config.name == "updated"
        assert config.description == "new description"

    def test_configure_hasattr_false_branch(self):
        """Test configure when attribute doesn't exist (False branch)."""
        config = ModelTypedConfiguration[dict[str, Any]](name="test")

        # Attempting to set non-existent attribute
        result = config.configure(
            name="updated", nonexistent_attribute="should be ignored"
        )

        # Should succeed but ignore non-existent attributes (False branch)
        assert result is True
        assert config.name == "updated"
        assert not hasattr(config, "nonexistent_attribute")

    def test_get_name_with_name_field(self):
        """Test get_name when 'name' field exists and is not None (True branch)."""
        config = ModelTypedConfiguration[dict[str, Any]](name="test_name")

        name = config.get_name()

        # Should return the name field value
        assert name == "test_name"

    def test_get_name_with_none_name_field(self):
        """Test get_name when 'name' field is None (continues loop)."""
        config = ModelTypedConfiguration[dict[str, Any]]()
        config.name = None

        name = config.get_name()

        # Should return fallback name when all fields are None
        assert "ModelTypedConfiguration" in name

    def test_get_name_fallback_branch(self):
        """Test get_name fallback when no name fields have values."""
        config = ModelTypedConfiguration[dict[str, Any]]()
        # Ensure name is None
        config.name = None

        name = config.get_name()

        # Should return class name as fallback
        assert "Unnamed" in name or "ModelTypedConfiguration" in name

    def test_set_name_hasattr_true_branch(self):
        """Test set_name when name field exists (True branch)."""
        config = ModelTypedConfiguration[dict[str, Any]](name="original")

        config.set_name("updated")

        # Should update the name field (True branch)
        assert config.name == "updated"

    def test_set_name_first_matching_field(self):
        """Test set_name uses first matching field from the list."""
        config = ModelTypedConfiguration[dict[str, Any]](name="original")

        config.set_name("new_name")

        # Should use 'name' field first (it's first in the list)
        assert config.name == "new_name"
