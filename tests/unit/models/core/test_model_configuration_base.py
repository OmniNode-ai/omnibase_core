"""
Tests for ModelConfigurationBase and related classes.

Verifies the generic configuration base classes provide
standardized configuration patterns and utilities.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.core import (
    ModelConfigurationBase,
    ModelTypedConfiguration,
)
from omnibase_core.models.metadata.model_semver import (
    parse_semver_from_string,
)


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

        config.version = parse_semver_from_string("2.0.0")
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
