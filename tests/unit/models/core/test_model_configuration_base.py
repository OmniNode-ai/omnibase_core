"""
Tests for ModelConfigurationBase and related classes.

Verifies the generic configuration base classes provide
standardized configuration patterns and utilities.
"""

import pytest
from datetime import datetime, UTC
from pydantic import BaseModel, Field
from typing import Optional

from src.omnibase_core.models.core.model_configuration_base import (
    ModelConfigurationBase,
    ModelTypedConfiguration,
    ModelSimpleConfiguration,
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
        config = ModelConfigurationBase[SampleConfigData].create_disabled("disabled_test")

        assert config.name == "disabled_test"
        assert config.enabled is False
        assert config.description == "Disabled disabled_test configuration"

    def test_get_config_value(self):
        """Test configuration value retrieval."""
        data = SampleConfigData(endpoint="http://localhost", port=9000)
        config = ModelConfigurationBase.create_with_data("test", data)

        assert config.get_config_value("endpoint") == "http://localhost"
        assert config.get_config_value("port") == 9000
        assert config.get_config_value("ssl_enabled") is False
        assert config.get_config_value("nonexistent", "default") == "default"

    def test_utility_methods(self):
        """Test utility methods."""
        config = ModelConfigurationBase[SampleConfigData](name="test")

        assert config.is_enabled() is True
        assert config.is_valid() is False  # No config_data
        assert config.get_display_name() == "test"
        assert config.get_version_or_default() == "1.0.0"

        config.enabled = False
        assert config.is_enabled() is False

        config.version = "2.0.0"
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
        assert config.get_custom_value("env") == "production"

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
        assert config1.get_custom_value("env") == "production"  # Overridden
        assert config1.get_custom_value("timeout") == 30.0  # Preserved
        assert config1.get_custom_value("debug") is False  # Added

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
        assert copy.get_custom_value("env") == "test"

        # Verify changes don't affect original
        copy.set_custom_string("env", "modified")
        assert original.get_custom_value("env") == "test"
        assert copy.get_custom_value("env") == "modified"

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
            description="Original description"
        )

        config.disable_with_reason("Service unavailable")

        assert config.enabled is False
        assert "Disabled: Service unavailable" in config.description


class TestModelSimpleConfiguration:
    """Test the simple configuration class."""

    def test_basic_functionality(self):
        """Test basic simple configuration functionality."""
        config = ModelSimpleConfiguration(name="simple_test")

        assert config.config_data is None

        config.set_config_value("timeout", 30)
        config.set_config_value("endpoint", "http://localhost")
        config.set_config_value("ssl", True)

        assert config.get_config_value("timeout") == 30
        assert config.get_config_value("endpoint") == "http://localhost"
        assert config.get_config_value("ssl") is True
        assert config.has_config_value("timeout") is True
        assert config.has_config_value("nonexistent") is False

    def test_value_removal(self):
        """Test configuration value removal."""
        config = ModelSimpleConfiguration(name="test")
        config.set_config_value("key1", "value1")
        config.set_config_value("key2", "value2")

        assert config.remove_config_value("key1") is True
        assert config.has_config_value("key1") is False
        assert config.has_config_value("key2") is True

        assert config.remove_config_value("nonexistent") is False

    def test_get_all_values(self):
        """Test getting all configuration values."""
        config = ModelSimpleConfiguration(name="test")
        config.set_config_value("key1", "value1")
        config.set_config_value("key2", 42)
        config.set_config_value("key3", True)

        all_values = config.get_all_config_values()
        expected = {"key1": "value1", "key2": 42, "key3": True}
        assert all_values == expected

    def test_create_from_dict(self):
        """Test creation from dictionary."""
        config_dict = {
            "timeout": 30,
            "endpoint": "http://localhost",
            "ssl": True,
            "retries": 3
        }

        config = ModelSimpleConfiguration.create_from_dict("dict_test", config_dict)

        assert config.name == "dict_test"
        assert config.get_config_value("timeout") == 30
        assert config.get_config_value("endpoint") == "http://localhost"
        assert config.get_config_value("ssl") is True
        assert config.get_config_value("retries") == 3

    def test_empty_configuration_handling(self):
        """Test handling of empty configurations."""
        config = ModelSimpleConfiguration(name="empty")

        assert config.get_all_config_values() == {}
        assert config.has_config_value("anything") is False
        assert config.remove_config_value("anything") is False
        assert config.get_config_value("anything", "default") == "default"


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
                return f"{protocol}://{self.config_data.endpoint}:{self.config_data.port}"

        data = SampleConfigData(
            endpoint="api.example.com",
            port=443,
            ssl_enabled=True
        )
        config = CustomConfig.create_with_data("custom", data)

        # Test base functionality
        assert config.name == "custom"
        assert config.is_enabled() is True

        # Test custom functionality
        assert config.get_full_endpoint() == "https://api.example.com:443"

        # Test custom properties
        config.set_custom_string("region", "us-east-1")
        assert config.get_custom_value("region") == "us-east-1"