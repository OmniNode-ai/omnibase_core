"""
Tests for ModelConfigurationBase and related classes.

Verifies the generic configuration base classes provide
standardized configuration patterns and utilities.
"""

from datetime import datetime

import pytest
from pydantic import BaseModel, Field

pytestmark = pytest.mark.unit

from omnibase_core.models.core import ModelConfigurationBase, ModelTypedConfiguration
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class SampleConfigData(BaseModel):
    """Sample typed configuration data for testing."""

    endpoint: str = Field(..., description="Service endpoint")
    port: int = Field(default=8080, description="Service port")
    ssl_enabled: bool = Field(default=False, description="Enable SSL")
    timeout: float = Field(default=30.0, description="Request timeout")


class TestModelConfigurationBase:
    """Test the base configuration class."""

    def test_basic_creation(self):
        """Test basic configuration creation."""
        config = ModelConfigurationBase[SampleConfigData]()

        assert config.name is None
        assert config.description is None
        assert config.version is None
        assert config.enabled is True
        assert config.config_data is None
        assert isinstance(config.created_at, datetime)
        assert isinstance(config.updated_at, datetime)

    def test_creation_with_data(self):
        """Test configuration creation with data."""
        data = SampleConfigData(endpoint="http://localhost")
        config = ModelConfigurationBase.create_with_data("test_config", data)

        assert config.name == "test_config"
        assert config.config_data == data
        assert config.enabled is True

    def test_empty_configuration(self):
        """Test empty configuration creation."""
        config = ModelConfigurationBase[SampleConfigData].create_empty("empty_test")

        assert config.name == "empty_test"
        assert config.description == "Empty empty_test configuration"
        assert config.config_data is None

    def test_disabled_configuration(self):
        """Test disabled configuration creation."""
        config = ModelConfigurationBase[SampleConfigData].create_disabled(
            "disabled_test",
        )

        assert config.name == "disabled_test"
        assert config.enabled is False
        assert config.description == "Disabled disabled_test configuration"

    def test_get_config_value(self):
        """Test configuration value retrieval."""
        data = SampleConfigData(endpoint="http://localhost", port=9000)
        config = ModelConfigurationBase.create_with_data("test", data)

        endpoint_result = config.get_config_value("endpoint")
        assert endpoint_result.is_ok()
        assert endpoint_result.unwrap().string_value == "http://localhost"

        port_result = config.get_config_value("port")
        assert port_result.is_ok()
        assert port_result.unwrap().number_value == 9000

        ssl_result = config.get_config_value("ssl_enabled")
        assert ssl_result.is_ok()
        assert ssl_result.unwrap().boolean_value is False

        # Test with default value
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue

        default_val = ModelSchemaValue.from_value("default")
        default_result = config.get_config_value("nonexistent", default_val)
        assert default_result.is_ok()
        assert default_result.unwrap().string_value == "default"

    def test_utility_methods(self):
        """Test utility methods."""
        config = ModelConfigurationBase[SampleConfigData](name="test")

        assert config.is_enabled() is True
        assert config.validate_instance() is False  # No config_data
        assert config.get_display_name() == "test"
        assert config.get_version_or_default() == "1.0.0"

        config.enabled = False
        assert config.is_enabled() is False

        config.version = ModelSemVer(major=2, minor=0, patch=0)
        assert config.get_version_or_default() == "2.0.0"

    def test_timestamp_update(self):
        """Test timestamp updating."""
        config = ModelConfigurationBase[SampleConfigData]()
        original_updated = config.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        config.update_timestamp()
        assert config.updated_at > original_updated


class TestModelTypedConfiguration:
    """Test the typed configuration with custom properties."""

    def test_basic_functionality(self):
        """Test basic typed configuration functionality."""
        data = SampleConfigData(endpoint="http://localhost")
        config = ModelTypedConfiguration.create_with_data("typed_test", data)

        # Base functionality
        assert config.name == "typed_test"
        assert config.config_data == data

        # Custom properties functionality
        assert config.is_empty() is True
        config.set_custom_string("env", "production")
        config.set_custom_number("max_connections", 100.0)
        config.set_custom_flag("debug", True)

        assert config.is_empty() is False
        assert config.get_field_count() == 3
        env_result = config.get_custom_value_wrapped("env")
        assert env_result.is_ok()
        assert env_result.unwrap().string_value == "production"

    def test_configuration_merging(self):
        """Test configuration merging."""
        data1 = SampleConfigData(endpoint="http://localhost")
        config1 = ModelTypedConfiguration.create_with_data("config1", data1)
        config1.set_custom_string("env", "staging")
        config1.set_custom_number("timeout", 30.0)

        data2 = SampleConfigData(endpoint="http://prod", port=443, ssl_enabled=True)
        config2 = ModelTypedConfiguration.create_with_data("config2", data2)
        config2.set_custom_string("env", "production")  # Should override
        config2.set_custom_flag("debug", False)

        original_updated = config1.updated_at
        config1.merge_configuration(config2)

        # Check merged data
        assert config1.name == "config2"  # Overridden
        assert config1.config_data.endpoint == "http://prod"  # Overridden
        assert config1.config_data.ssl_enabled is True

        # Check merged custom properties
        env_result = config1.get_custom_value_wrapped("env")
        assert env_result.is_ok()
        assert env_result.unwrap().string_value == "production"  # Overridden

        timeout_result = config1.get_custom_value_wrapped("timeout")
        assert timeout_result.is_ok()
        assert timeout_result.unwrap().number_value == 30.0  # Preserved

        debug_result = config1.get_custom_value_wrapped("debug")
        assert debug_result.is_ok()
        assert debug_result.unwrap().boolean_value is False  # Added

        # Check timestamp was updated
        assert config1.updated_at > original_updated

    def test_configuration_copying(self):
        """Test configuration copying."""
        data = SampleConfigData(endpoint="http://localhost")
        original = ModelTypedConfiguration.create_with_data("original", data)
        original.set_custom_string("env", "test")

        copy = original.copy_configuration()

        # Verify it's a deep copy
        assert copy.name == original.name
        assert copy.config_data.endpoint == original.config_data.endpoint
        env_result = copy.get_custom_value_wrapped("env")
        assert env_result.is_ok()
        assert env_result.unwrap().string_value == "test"

        # Verify changes don't affect original
        copy.set_custom_string("env", "modified")

        original_env_result = original.get_custom_value_wrapped("env")
        assert original_env_result.is_ok()
        assert original_env_result.unwrap().string_value == "test"

        copy_env_result = copy.get_custom_value_wrapped("env")
        assert copy_env_result.is_ok()
        assert copy_env_result.unwrap().string_value == "modified"

    def test_validate_and_enable(self):
        """Test validation and enabling."""
        config = ModelTypedConfiguration[SampleConfigData](name="test")

        # Should fail without config_data
        assert config.validate_and_enable() is False
        assert config.enabled is True  # Default, not changed

        # Should succeed with config_data
        config.config_data = SampleConfigData(endpoint="http://localhost")
        assert config.validate_and_enable() is True
        assert config.enabled is True

    def test_disable_with_reason(self):
        """Test disabling with reason."""
        config = ModelTypedConfiguration[SampleConfigData](
            name="test",
            description="Original description",
        )

        config.disable_with_reason("Service unavailable")

        assert config.enabled is False
        assert "Disabled: Service unavailable" in config.description


class TestConfigurationIntegration:
    """Test integration scenarios and edge cases."""

    def test_generic_type_preservation(self):
        """Test that generic types are preserved correctly."""
        # Test with different data types
        str_config = ModelConfigurationBase[str]()
        str_config.config_data = "test string"
        assert isinstance(str_config.config_data, str)

        dict_config = ModelConfigurationBase[dict[str, int]]()
        dict_config.config_data = {"count": 42}
        assert isinstance(str_config.config_data, str)
        assert isinstance(dict_config.config_data, dict)

    def test_inheritance_patterns(self):
        """Test inheritance patterns work correctly."""

        class CustomConfig(ModelTypedConfiguration[SampleConfigData]):
            """Custom configuration with additional methods."""

            def get_full_endpoint(self) -> str:
                """Get full endpoint with protocol."""
                if not self.config_data:
                    return "http://localhost:8080"

                protocol = "https" if self.config_data.ssl_enabled else "http"
                return (
                    f"{protocol}://{self.config_data.endpoint}:{self.config_data.port}"
                )

        data = SampleConfigData(endpoint="api.example.com", port=443, ssl_enabled=True)
        config = CustomConfig.create_with_data("custom", data)

        # Test base functionality
        assert config.name == "custom"
        assert config.is_enabled() is True

        # Test custom functionality
        assert config.get_full_endpoint() == "https://api.example.com:443"

        # Test custom properties
        config.set_custom_string("region", "us-east-1")
        region_result = config.get_custom_value_wrapped("region")
        assert region_result.is_ok()
        assert region_result.unwrap().string_value == "us-east-1"


class TestConfigurationBaseEdgeCases:
    """Test edge cases and error handling for ModelConfigurationBase."""

    def test_serialize_config_data_with_exception(self):
        """Test that Exception objects in config_data are serialized to strings."""
        config = ModelConfigurationBase[Exception](
            name="error_config",
        )
        config.config_data = ValueError("Test error message")

        # Exception should be converted to string during serialization
        serialized = config.serialize()
        assert serialized["config_data"] == "Test error message"

    def test_serialize_config_data_with_complex_object(self):
        """Test serialization of complex objects with __dict__."""

        class ComplexObject:
            def __init__(self):
                self.field1 = "value1"
                self.field2 = 42
                self.field3 = True

        config = ModelConfigurationBase[ComplexObject](name="complex_config")
        config.config_data = ComplexObject()

        # Object with __dict__ should serialize its attributes
        serialized = config.serialize()
        assert serialized["config_data"]["field1"] == "value1"
        assert serialized["config_data"]["field2"] == 42
        assert serialized["config_data"]["field3"] is True

    def test_serialize_config_data_with_pydantic_model(self):
        """Test serialization of Pydantic models in config_data."""
        config = ModelConfigurationBase[SampleConfigData](
            name="pydantic_config",
        )
        config.config_data = SampleConfigData(
            endpoint="http://test",
            port=8080,
            ssl_enabled=True,
        )

        # Pydantic models should serialize properly
        serialized = config.serialize()
        assert serialized["config_data"]["endpoint"] == "http://test"
        assert serialized["config_data"]["port"] == 8080
        assert serialized["config_data"]["ssl_enabled"] is True

    def test_validate_config_data_with_exception_object(self):
        """Test that Exception in config_data is converted during validation."""
        # When creating config with Exception as config_data
        error = RuntimeError("Configuration error")
        config = ModelConfigurationBase[str](
            name="test",
            config_data=error,
        )

        # Should be converted to string during validation
        assert isinstance(config.config_data, str)
        assert config.config_data == "Configuration error"

    def test_get_config_value_with_unsupported_type(self):
        """Test get_config_value with value of unsupported type."""

        class CustomData:
            unsupported_field = object()  # Not str, int, bool, or float

        config = ModelConfigurationBase[CustomData](name="test")
        config.config_data = CustomData()

        # Should return error for unsupported type without default
        result = config.get_config_value("unsupported_field")
        assert result.is_err()
        assert "unsupported type" in result.error

    def test_get_config_value_with_unsupported_type_and_default(self):
        """Test get_config_value returns default for unsupported types."""
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue

        class CustomData:
            unsupported_field = object()

        config = ModelConfigurationBase[CustomData](name="test")
        config.config_data = CustomData()

        default_value = ModelSchemaValue.from_value("default")
        result = config.get_config_value("unsupported_field", default_value)
        assert result.is_ok()
        assert result.unwrap().string_value == "default"

    def test_get_config_value_missing_key_without_default(self):
        """Test get_config_value with missing key and no default."""
        data = SampleConfigData(endpoint="http://localhost")
        config = ModelConfigurationBase.create_with_data("test", data)

        result = config.get_config_value("nonexistent_key")
        assert result.is_err()
        assert "not found" in result.error

    def test_get_config_value_with_none_config_data(self):
        """Test get_config_value when config_data is None."""
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue

        config = ModelConfigurationBase[SampleConfigData](name="test")

        # Without default
        result = config.get_config_value("any_key")
        assert result.is_err()
        assert "not found" in result.error

        # With default
        default_value = ModelSchemaValue.from_value("default")
        result_with_default = config.get_config_value("any_key", default_value)
        assert result_with_default.is_ok()
        assert result_with_default.unwrap().string_value == "default"

    def test_validate_instance_with_empty_name(self):
        """Test that validate_instance returns False for empty string name."""
        data = SampleConfigData(endpoint="http://localhost")
        config = ModelConfigurationBase.create_with_data("", data)

        # Empty name should fail validation
        assert config.validate_instance() is False

    def test_validate_instance_with_whitespace_name(self):
        """Test that validate_instance returns False for whitespace-only name."""
        data = SampleConfigData(endpoint="http://localhost")
        config = ModelConfigurationBase.create_with_data("   ", data)

        # Whitespace-only name should fail validation
        assert config.validate_instance() is False

    def test_validate_instance_when_disabled(self):
        """Test that validate_instance returns False when config is disabled."""
        data = SampleConfigData(endpoint="http://localhost")
        config = ModelConfigurationBase.create_with_data("test", data)
        config.enabled = False

        # Disabled config should fail validation
        assert config.validate_instance() is False

    def test_validate_instance_with_none_config_data(self):
        """Test that validate_instance returns False when config_data is None."""
        config = ModelConfigurationBase[SampleConfigData](name="test")

        # None config_data should fail validation
        assert config.validate_instance() is False

    def test_validate_instance_success(self):
        """Test that validate_instance returns True for valid configuration."""
        data = SampleConfigData(endpoint="http://localhost")
        config = ModelConfigurationBase.create_with_data("test", data)

        assert config.validate_instance() is True

    def test_configure_method_basic(self):
        """Test configure method updates configuration fields."""
        config = ModelConfigurationBase[SampleConfigData](name="original")

        result = config.configure(name="updated", description="New description")

        assert result is True
        assert config.name == "updated"
        assert config.description == "New description"

    def test_configure_method_updates_config_data(self):
        """Test configure method can update config_data."""
        config = ModelConfigurationBase[SampleConfigData](name="test")

        new_data = SampleConfigData(endpoint="http://updated")
        result = config.configure(config_data=new_data)

        assert result is True
        assert config.config_data == new_data

    def test_configure_method_updates_timestamp(self):
        """Test that configure method updates the timestamp."""
        import time

        config = ModelConfigurationBase[SampleConfigData](name="test")
        original_updated = config.updated_at

        time.sleep(0.01)
        config.configure(description="Updated")

        assert config.updated_at > original_updated

    def test_get_display_name_with_none_name(self):
        """Test get_display_name falls back to default when name is None."""
        config = ModelConfigurationBase[SampleConfigData]()

        assert config.get_display_name() == "Unnamed Configuration"

    def test_get_display_name_with_set_name(self):
        """Test get_display_name returns actual name when set."""
        config = ModelConfigurationBase[SampleConfigData](name="MyConfig")

        assert config.get_display_name() == "MyConfig"

    def test_serialize_method(self):
        """Test serialize method returns proper dictionary."""
        data = SampleConfigData(endpoint="http://localhost", port=9000)
        config = ModelConfigurationBase.create_with_data("test", data)
        config.version = ModelSemVer(major=1, minor=2, patch=3)

        serialized = config.serialize()

        assert isinstance(serialized, dict)
        assert serialized["name"] == "test"
        assert serialized["enabled"] is True
        assert "config_data" in serialized
        assert "created_at" in serialized

    def test_serialize_excludes_none_false(self):
        """Test serialize includes None values when exclude_none=False."""
        config = ModelConfigurationBase[SampleConfigData]()

        serialized = config.serialize()

        # Should include None values
        assert "name" in serialized
        assert serialized["name"] is None
        assert "description" in serialized
        assert serialized["description"] is None

    def test_get_name_protocol_method(self):
        """Test get_name protocol method implementation."""
        config = ModelConfigurationBase[SampleConfigData](name="TestConfig")

        assert config.get_name() == "TestConfig"

    def test_get_name_with_none_name(self):
        """Test get_name returns default when name is None."""
        config = ModelConfigurationBase[SampleConfigData]()

        assert config.get_name() == "Unnamed Configuration"

    def test_set_name_protocol_method(self):
        """Test set_name protocol method implementation."""
        config = ModelConfigurationBase[SampleConfigData](name="original")

        config.set_name("updated")

        assert config.name == "updated"

    def test_set_name_updates_timestamp(self):
        """Test that set_name updates the timestamp."""
        import time

        config = ModelConfigurationBase[SampleConfigData](name="original")
        original_updated = config.updated_at

        time.sleep(0.01)
        config.set_name("updated")

        assert config.updated_at > original_updated

    def test_version_or_default_with_none(self):
        """Test get_version_or_default returns default when version is None."""
        config = ModelConfigurationBase[SampleConfigData](name="test")

        assert config.get_version_or_default() == "1.0.0"

    def test_version_or_default_with_set_version(self):
        """Test get_version_or_default returns actual version when set."""
        config = ModelConfigurationBase[SampleConfigData](name="test")
        config.version = ModelSemVer(major=3, minor=2, patch=1)

        assert config.get_version_or_default() == "3.2.1"

    def test_model_validator_default_implementation(self):
        """Test that default model_validator returns self."""
        config = ModelConfigurationBase[SampleConfigData](name="test")

        # Should not raise and should return valid config
        assert config.name == "test"
        assert config.enabled is True


class TestConfigurationBaseProtocolCompliance:
    """Test protocol compliance for Serializable, Configurable, Nameable, Validatable."""

    def test_serializable_protocol_serialize(self):
        """Test Serializable protocol serialize method."""
        data = SampleConfigData(endpoint="http://localhost")
        config = ModelConfigurationBase.create_with_data("test", data)

        serialized = config.serialize()

        assert isinstance(serialized, dict)
        assert "name" in serialized
        assert "config_data" in serialized

    def test_configurable_protocol_configure(self):
        """Test Configurable protocol configure method."""
        config = ModelConfigurationBase[SampleConfigData](name="test")

        success = config.configure(
            name="updated",
            description="Updated config",
            enabled=False,
        )

        assert success is True
        assert config.name == "updated"
        assert config.description == "Updated config"
        assert config.enabled is False

    def test_nameable_protocol_get_name(self):
        """Test Nameable protocol get_name method."""
        config = ModelConfigurationBase[SampleConfigData](name="TestName")

        name = config.get_name()

        assert name == "TestName"

    def test_nameable_protocol_set_name(self):
        """Test Nameable protocol set_name method."""
        config = ModelConfigurationBase[SampleConfigData](name="original")

        config.set_name("NewName")

        assert config.name == "NewName"

    def test_validatable_protocol_validate_instance(self):
        """Test Validatable protocol validate_instance method."""
        data = SampleConfigData(endpoint="http://localhost")
        config = ModelConfigurationBase.create_with_data("test", data)

        is_valid = config.validate_instance()

        assert is_valid is True

    def test_validatable_protocol_invalid_instance(self):
        """Test Validatable protocol returns False for invalid instance."""
        config = ModelConfigurationBase[SampleConfigData](name="test")
        # No config_data set

        is_valid = config.validate_instance()

        assert is_valid is False
