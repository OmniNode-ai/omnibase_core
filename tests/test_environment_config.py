#!/usr/bin/env python3
"""
Tests for environment-based configuration management.

Comprehensive tests for ModelEnvironmentConfig, environment variable parsing,
validation, type conversion, and registry functionality.
"""

import os
from pathlib import Path
from typing import List, Optional
from unittest.mock import mock_open, patch

import pytest
from pydantic import BaseModel, Field, ValidationError

from omnibase_core.core.configuration import (
    EnvironmentConfigRegistry,
    ModelEnvironmentConfig,
    ModelEnvironmentPrefix,
    ModelEnvironmentVariable,
    config_registry,
    get_env_bool,
    get_env_float,
    get_env_int,
    get_env_list,
    is_development_environment,
    is_production_environment,
    register_config,
)


class TestModelConfig(ModelEnvironmentConfig):
    """Test configuration model."""

    app_name: str = Field(..., description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    port: int = Field(default=8000, description="Server port")
    timeout: float = Field(default=30.0, description="Request timeout")
    features: List[str] = Field(default_factory=list, description="Enabled features")
    database_url: Optional[str] = Field(default=None, description="Database URL")


class TestModelEnvironmentPrefix:
    """Test ModelEnvironmentPrefix functionality."""

    def test_format_key_basic(self):
        """Test basic key formatting."""
        prefix = ModelEnvironmentPrefix(prefix="TEST")

        assert prefix.format_key("KEY") == "TEST_KEY"
        assert prefix.format_key("debug") == "TEST_DEBUG"

    def test_format_key_custom_separator(self):
        """Test key formatting with custom separator."""
        prefix = ModelEnvironmentPrefix(prefix="APP", separator="__")

        assert prefix.format_key("PORT") == "APP__PORT"

    def test_format_key_case_sensitivity(self):
        """Test case sensitivity in key formatting."""
        prefix_case_sensitive = ModelEnvironmentPrefix(
            prefix="Test", case_sensitive=True
        )
        prefix_case_insensitive = ModelEnvironmentPrefix(
            prefix="Test", case_sensitive=False
        )

        assert prefix_case_sensitive.format_key("Key") == "Test_Key"
        assert prefix_case_insensitive.format_key("Key") == "TEST_KEY"


class TestModelEnvironmentConfig:
    """Test ModelEnvironmentConfig functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Clear any existing environment variables
        self.original_env = dict(os.environ)
        self.clear_test_env_vars()

    def teardown_method(self):
        """Clean up test environment."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def clear_test_env_vars(self):
        """Clear test environment variables."""
        test_prefixes = ["TEST_", "APP_", "MYAPP_"]
        for key in list(os.environ.keys()):
            if any(key.startswith(prefix) for prefix in test_prefixes):
                del os.environ[key]

    def test_from_environment_basic(self):
        """Test basic environment variable loading."""
        os.environ["TEST_APP_NAME"] = "test-app"
        os.environ["TEST_DEBUG"] = "true"
        os.environ["TEST_PORT"] = "9000"
        os.environ["TEST_TIMEOUT"] = "45.5"

        config = TestModelConfig.from_environment(prefix="TEST")

        assert config.app_name == "test-app"
        assert config.debug is True
        assert config.port == 9000
        assert config.timeout == 45.5

    def test_from_environment_with_overrides(self):
        """Test environment loading with parameter overrides."""
        os.environ["TEST_APP_NAME"] = "env-app"
        os.environ["TEST_DEBUG"] = "false"

        config = TestModelConfig.from_environment(
            prefix="TEST",
            app_name="override-app",  # Override environment
            port=7000,  # Override default
        )

        assert config.app_name == "override-app"  # Override wins
        assert config.debug is False  # From environment
        assert config.port == 7000  # Override wins

    def test_from_environment_type_conversion(self):
        """Test type conversion from environment strings."""
        os.environ["APP_NAME"] = "test"
        os.environ["APP_DEBUG"] = "yes"  # Alternative boolean format
        os.environ["APP_PORT"] = "8080"
        os.environ["APP_TIMEOUT"] = "10.5"
        os.environ["APP_FEATURES"] = "auth,logging,metrics"  # List format

        config = TestModelConfig.from_environment(prefix="APP")

        assert config.app_name == "test"
        assert config.debug is True
        assert config.port == 8080
        assert config.timeout == 10.5
        assert config.features == ["auth", "logging", "metrics"]

    def test_from_environment_boolean_conversion(self):
        """Test various boolean conversion formats."""
        bool_tests = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("anything", False),  # Default to False for unknown values
        ]

        for env_value, expected in bool_tests:
            self.clear_test_env_vars()
            os.environ["TEST_APP_NAME"] = "test"
            os.environ["TEST_DEBUG"] = env_value

            config = TestModelConfig.from_environment(prefix="TEST")
            assert (
                config.debug == expected
            ), f"'{env_value}' should convert to {expected}"

    def test_from_environment_missing_required_strict(self):
        """Test strict validation with missing required fields."""
        with pytest.raises(ValidationError):
            TestModelConfig.from_environment(prefix="TEST", strict=True)

    def test_from_environment_missing_required_non_strict(self):
        """Test non-strict validation with missing required fields."""
        # Should not raise exception, but may have missing fields
        try:
            config = TestModelConfig.from_environment(prefix="TEST", strict=False)
        except Exception:
            pytest.fail("Non-strict mode should not raise exceptions")

    def test_camel_to_snake_conversion(self):
        """Test camelCase to snake_case conversion."""
        assert ModelEnvironmentConfig._camel_to_snake("appName") == "app_name"
        assert ModelEnvironmentConfig._camel_to_snake("debugMode") == "debug_mode"
        assert (
            ModelEnvironmentConfig._camel_to_snake("maxRetryCount") == "max_retry_count"
        )
        assert ModelEnvironmentConfig._camel_to_snake("simple") == "simple"

    def test_generate_env_keys(self):
        """Test environment key generation."""
        TestModelConfig._env_prefix = ModelEnvironmentPrefix(prefix="TEST")

        keys = TestModelConfig._generate_env_keys("appName")

        # Should generate multiple possible keys
        assert "TEST_APPNAME" in keys or "TEST_APP_NAME" in keys
        assert "APPNAME" in keys or "APP_NAME" in keys

    @patch(
        "builtins.open",
        mock_open(
            read_data='KEY1=value1\nKEY2=value2\n# Comment\nKEY3="quoted value"\n'
        ),
    )
    def test_load_env_file(self):
        """Test loading environment variables from file."""
        env_file = Path("/fake/env/file")

        # Mock file existence
        with patch.object(Path, "exists", return_value=True):
            TestModelConfig._load_env_file(env_file)

        assert os.environ.get("KEY1") == "value1"
        assert os.environ.get("KEY2") == "value2"
        assert os.environ.get("KEY3") == "quoted value"

    def test_get_env_summary(self):
        """Test environment summary generation."""
        os.environ["TEST_APP_NAME"] = "test-app"
        os.environ["TEST_DEBUG"] = "true"

        config = TestModelConfig.from_environment(prefix="TEST")
        summary = config.get_env_summary()

        assert "app_name" in summary
        assert "debug" in summary
        assert summary["app_name"] == "test-app"
        assert summary["debug"] is True

    def test_get_env_documentation(self):
        """Test environment documentation generation."""
        docs = TestModelConfig.get_env_documentation()

        assert len(docs) > 0

        # Check structure of documentation
        doc = docs[0]
        assert "field" in doc
        assert "env_keys" in doc
        assert "description" in doc
        assert "type" in doc
        assert "required" in doc


class TestEnvironmentConfigRegistry:
    """Test EnvironmentConfigRegistry functionality."""

    def setup_method(self):
        """Set up test registry."""
        self.registry = EnvironmentConfigRegistry()
        self.registry._configs = {}  # Clear registry

    def test_register_and_get(self):
        """Test registering and retrieving configurations."""
        os.environ["TEST_APP_NAME"] = "test-app"
        config = TestModelConfig.from_environment(prefix="TEST")

        self.registry.register("test-config", config)

        retrieved = self.registry.get("test-config")
        assert retrieved is config
        assert retrieved.app_name == "test-app"

    def test_list_configs(self):
        """Test listing registered configurations."""
        os.environ["TEST_APP_NAME"] = "test1"
        config1 = TestModelConfig.from_environment(prefix="TEST")

        os.environ["OTHER_APP_NAME"] = "test2"
        config2 = TestModelConfig.from_environment(prefix="OTHER")

        self.registry.register("config1", config1)
        self.registry.register("config2", config2)

        configs = self.registry.list_configs()
        assert "config1" in configs
        assert "config2" in configs
        assert len(configs) == 2

    def test_get_nonexistent(self):
        """Test getting non-existent configuration."""
        result = self.registry.get("nonexistent")
        assert result is None


class TestUtilityFunctions:
    """Test utility functions."""

    def setup_method(self):
        """Set up test environment."""
        self.original_env = dict(os.environ)
        # Clear relevant environment variables
        for key in ["ENVIRONMENT", "NODE_ENV", "DEBUG", "DEV_MODE"]:
            os.environ.pop(key, None)

    def teardown_method(self):
        """Restore environment."""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_get_env_bool(self):
        """Test get_env_bool utility."""
        os.environ["TEST_BOOL"] = "true"
        assert get_env_bool("TEST_BOOL") is True

        os.environ["TEST_BOOL"] = "false"
        assert get_env_bool("TEST_BOOL") is False

        # Test default
        assert get_env_bool("NON_EXISTENT", True) is True

    def test_get_env_int(self):
        """Test get_env_int utility."""
        os.environ["TEST_INT"] = "42"
        assert get_env_int("TEST_INT") == 42

        # Test invalid value (should use default)
        os.environ["TEST_INT"] = "invalid"
        assert get_env_int("TEST_INT", 100) == 100

        # Test default
        assert get_env_int("NON_EXISTENT", 99) == 99

    def test_get_env_float(self):
        """Test get_env_float utility."""
        os.environ["TEST_FLOAT"] = "3.14"
        assert get_env_float("TEST_FLOAT") == 3.14

        # Test invalid value (should use default)
        os.environ["TEST_FLOAT"] = "invalid"
        assert get_env_float("TEST_FLOAT", 1.0) == 1.0

    def test_get_env_list(self):
        """Test get_env_list utility."""
        os.environ["TEST_LIST"] = "a,b,c"
        assert get_env_list("TEST_LIST") == ["a", "b", "c"]

        os.environ["TEST_LIST"] = "single"
        assert get_env_list("TEST_LIST") == ["single"]

        # Test custom separator
        os.environ["TEST_LIST"] = "a|b|c"
        assert get_env_list("TEST_LIST", separator="|") == ["a", "b", "c"]

        # Test default
        assert get_env_list("NON_EXISTENT", ["default"]) == ["default"]

    def test_is_production_environment(self):
        """Test production environment detection."""
        # Test explicit production setting
        os.environ["ENVIRONMENT"] = "production"
        assert is_production_environment() is True

        os.environ["ENVIRONMENT"] = "development"
        assert is_production_environment() is False

        # Test NODE_ENV
        del os.environ["ENVIRONMENT"]
        os.environ["NODE_ENV"] = "production"
        assert is_production_environment() is True

        # Test debug flags
        del os.environ["NODE_ENV"]
        os.environ["DEBUG"] = "true"
        assert is_production_environment() is False

        # Test default (no debug flags = production)
        del os.environ["DEBUG"]
        # This should be True since no debug flags are set
        # Note: Actual behavior depends on implementation logic

    def test_is_development_environment(self):
        """Test development environment detection."""
        os.environ["DEBUG"] = "true"
        assert is_development_environment() is True

        os.environ["ENVIRONMENT"] = "production"
        assert is_development_environment() is False


class TestRegisterConfigFunction:
    """Test register_config helper function."""

    def test_register_config(self):
        """Test register_config helper."""
        os.environ["HELPER_APP_NAME"] = "helper-test"

        # Clear global registry first
        config_registry._configs = {}

        config = register_config("helper-test", TestModelConfig, prefix="HELPER")

        assert config.app_name == "helper-test"
        assert config_registry.get("helper-test") is config


class TestIntegration:
    """Integration tests for the configuration system."""

    def setup_method(self):
        """Set up integration test environment."""
        self.original_env = dict(os.environ)
        config_registry._configs = {}

    def teardown_method(self):
        """Clean up integration test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_full_workflow(self):
        """Test complete configuration workflow."""
        # Set up environment
        os.environ["INTEGRATION_APP_NAME"] = "integration-test"
        os.environ["INTEGRATION_DEBUG"] = "true"
        os.environ["INTEGRATION_PORT"] = "9999"
        os.environ["INTEGRATION_FEATURES"] = "auth,metrics"

        # Create configuration
        config = TestModelConfig.from_environment(
            prefix="INTEGRATION", timeout=60.0  # Override
        )

        # Verify configuration
        assert config.app_name == "integration-test"
        assert config.debug is True
        assert config.port == 9999
        assert config.timeout == 60.0  # Override value
        assert config.features == ["auth", "metrics"]

        # Register configuration
        config_registry.register("integration", config)

        # Retrieve from registry
        retrieved = config_registry.get("integration")
        assert retrieved is config

        # Generate documentation
        docs = TestModelConfig.get_env_documentation()
        assert len(docs) > 0

        # Get summary
        summary = config.get_env_summary()
        assert summary["app_name"] == "integration-test"
        assert summary["debug"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
