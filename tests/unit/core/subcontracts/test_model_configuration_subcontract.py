#!/usr/bin/env python3
"""
Unit tests for ModelConfigurationSubcontract.

Tests configuration management subcontract including validation,
source management, environment integration, and runtime behavior.
"""

import re
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.subcontracts.model_configuration_subcontract import (
    ModelConfigurationSource,
    ModelConfigurationSubcontract,
    ModelConfigurationValidation,
)
from omnibase_core.enums.enum_environment import EnumEnvironment
from omnibase_core.enums.enum_log_level import EnumLogLevel


class TestModelConfigurationSource:
    """Test suite for ModelConfigurationSource."""

    def test_valid_source_creation(self):
        """Test creating a valid configuration source."""
        source = ModelConfigurationSource(
            source_type="file",
            source_path="/path/to/config.yaml",
            priority=50,
            required=True,
            watch_for_changes=True,
        )

        assert source.source_type == "file"
        assert source.source_path == "/path/to/config.yaml"
        assert source.priority == 50
        assert source.required is True
        assert source.watch_for_changes is True

    def test_source_defaults(self):
        """Test configuration source defaults."""
        source = ModelConfigurationSource(source_type="environment")

        assert source.source_type == "environment"
        assert source.source_path is None
        assert source.priority == 100
        assert source.required is False
        assert source.watch_for_changes is False

    def test_invalid_source_type_pattern(self):
        """Test validation of source_type pattern."""
        with pytest.raises(ValidationError):
            ModelConfigurationSource(source_type="invalid-type")  # Hyphen not allowed

        with pytest.raises(ValidationError):
            ModelConfigurationSource(source_type="Invalid")  # Uppercase not allowed

    def test_priority_validation(self):
        """Test priority value validation."""
        # Valid priorities
        valid_priorities = [0, 100, 500, 1000]
        for priority in valid_priorities:
            source = ModelConfigurationSource(source_type="file", priority=priority)
            assert source.priority == priority

        # Invalid priorities
        with pytest.raises(ValidationError):
            ModelConfigurationSource(source_type="file", priority=-1)

        with pytest.raises(ValidationError):
            ModelConfigurationSource(source_type="file", priority=1001)


class TestModelConfigurationValidation:
    """Test suite for ModelConfigurationValidation."""

    def test_valid_validation_creation(self):
        """Test creating valid configuration validation."""
        validation = ModelConfigurationValidation(
            required_keys=["database_url", "api_key"],
            optional_keys=["debug_mode", "log_level"],
            validation_schema={"database_url": "string", "api_key": "string"},
            environment_specific={
                EnumEnvironment.PRODUCTION: {"ssl_required": "required"},
                EnumEnvironment.DEVELOPMENT: {"debug_mode": "optional"},
            },
            sensitive_keys=["api_key", "database_password"],
        )

        assert validation.required_keys == ["database_url", "api_key"]
        assert validation.optional_keys == ["debug_mode", "log_level"]
        assert validation.validation_schema["database_url"] == "string"
        assert EnumEnvironment.PRODUCTION in validation.environment_specific
        assert validation.sensitive_keys == ["api_key", "database_password"]

    def test_validation_defaults(self):
        """Test validation defaults."""
        validation = ModelConfigurationValidation()

        assert validation.required_keys == []
        assert validation.optional_keys == []
        assert validation.validation_schema is None
        assert validation.environment_specific == {}
        assert validation.sensitive_keys == []


class TestModelConfigurationSubcontract:
    """Test suite for ModelConfigurationSubcontract."""

    def test_minimal_valid_subcontract(self):
        """Test creating subcontract with minimal required fields."""
        subcontract = ModelConfigurationSubcontract(config_name="test-config")

        assert subcontract.config_name == "test-config"
        assert subcontract.config_version == "1.0.0"
        assert subcontract.target_environment == EnumEnvironment.DEVELOPMENT
        assert subcontract.default_source_type == "file"
        assert subcontract.strict_validation is True

    def test_full_subcontract_creation(self):
        """Test creating subcontract with all fields specified."""
        validation_rules = ModelConfigurationValidation(
            required_keys=["database_url"], sensitive_keys=["api_key"]
        )

        sources = [
            ModelConfigurationSource(
                source_type="file",
                source_path="/etc/config.yaml",
                priority=10,
                required=True,
            ),
            ModelConfigurationSource(
                source_type="environment", priority=20, required=False
            ),
        ]

        subcontract = ModelConfigurationSubcontract(
            config_name="full-test-config",
            config_version="2.1.0",
            configuration_sources=sources,
            default_source_type="database",
            target_environment=EnumEnvironment.PRODUCTION,
            environment_variable_prefix="MYAPP_",
            inherit_environment=True,
            validation_rules=validation_rules,
            strict_validation=False,
            allow_runtime_updates=True,
            auto_reload_on_change=True,
            reload_debounce_seconds=10.0,
            encrypt_sensitive_values=False,
            backup_configuration=True,
            max_backup_versions=5,
            backup_directory=Path("/var/backups/config"),
        )

        assert subcontract.config_name == "full-test-config"
        assert subcontract.config_version == "2.1.0"
        assert len(subcontract.configuration_sources) == 2
        assert subcontract.default_source_type == "database"
        assert subcontract.target_environment == EnumEnvironment.PRODUCTION
        assert subcontract.environment_variable_prefix == "MYAPP_"
        assert subcontract.validation_rules.required_keys == ["database_url"]
        assert subcontract.strict_validation is False
        assert subcontract.allow_runtime_updates is True
        assert subcontract.reload_debounce_seconds == 10.0
        assert subcontract.max_backup_versions == 5

    def test_config_name_validation(self):
        """Test config_name validation rules."""
        # Valid names
        valid_names = ["test-config", "test_config", "TestConfig", "config123", "a"]

        for name in valid_names:
            config = ModelConfigurationSubcontract(config_name=name)
            assert config.config_name == name

        # Invalid names
        invalid_names = [
            "",  # Empty
            "123invalid",  # Starts with number
            "invalid config",  # Space
            "invalid@config",  # Special character
            "a" * 129,  # Too long
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError):
                ModelConfigurationSubcontract(config_name=name)

    def test_config_version_validation(self):
        """Test config_version validation pattern."""
        # Valid versions
        valid_versions = ["1.0.0", "2.1.3", "1.0.0-alpha", "2.0.0-beta.1", "3.2.1-rc.2"]

        for version in valid_versions:
            config = ModelConfigurationSubcontract(
                config_name="test", config_version=version
            )
            assert config.config_version == version

        # Invalid versions
        invalid_versions = [
            "1.0",  # Missing patch version
            "v1.0.0",  # Prefix not allowed
            "1.0.0.1",  # Too many parts
            "invalid-version",  # Non-semantic version
        ]

        for version in invalid_versions:
            with pytest.raises(ValidationError, match="String should match pattern"):
                ModelConfigurationSubcontract(
                    config_name="test", config_version=version
                )

    def test_environment_variable_prefix_validation(self):
        """Test environment variable prefix validation."""
        # Valid prefixes
        valid_prefixes = ["MYAPP_", "TEST_CONFIG_", "A_"]

        for prefix in valid_prefixes:
            config = ModelConfigurationSubcontract(
                config_name="test", environment_variable_prefix=prefix
            )
            assert config.environment_variable_prefix == prefix

        # Invalid prefixes
        invalid_prefixes = [
            "myapp_",  # Lowercase
            "123INVALID_",  # Starts with number
            "INVALID-PREFIX_",  # Hyphen not allowed
        ]

        for prefix in invalid_prefixes:
            with pytest.raises(ValidationError):
                ModelConfigurationSubcontract(
                    config_name="test", environment_variable_prefix=prefix
                )

    def test_reload_debounce_seconds_validation(self):
        """Test reload_debounce_seconds validation with minimum value."""
        # Valid values (>= 1.0)
        valid_values = [1.0, 5.0, 30.0, 300.0]

        for value in valid_values:
            config = ModelConfigurationSubcontract(
                config_name="test", reload_debounce_seconds=value
            )
            assert config.reload_debounce_seconds == value

        # Invalid values (< 1.0 or > 300.0)
        invalid_values = [0.0, 0.5, 0.9, 301.0, 500.0]

        for value in invalid_values:
            with pytest.raises(ValidationError):
                ModelConfigurationSubcontract(
                    config_name="test", reload_debounce_seconds=value
                )

    def test_max_backup_versions_validation(self):
        """Test max_backup_versions validation constraints."""
        # Valid values
        valid_values = [1, 10, 50, 100]

        for value in valid_values:
            config = ModelConfigurationSubcontract(
                config_name="test", max_backup_versions=value
            )
            assert config.max_backup_versions == value

        # Invalid values
        invalid_values = [0, -1, 101, 1000]

        for value in invalid_values:
            with pytest.raises(ValidationError):
                ModelConfigurationSubcontract(
                    config_name="test", max_backup_versions=value
                )

    def test_configuration_sources_validation_duplicate_priorities(self):
        """Test validation of duplicate priorities in required sources."""
        # Duplicate priorities in required sources should fail
        sources_with_duplicates = [
            ModelConfigurationSource(source_type="file", priority=10, required=True),
            ModelConfigurationSource(
                source_type="environment", priority=10, required=True  # Same priority
            ),
        ]

        with pytest.raises(ValidationError, match="duplicate priorities"):
            ModelConfigurationSubcontract(
                config_name="test", configuration_sources=sources_with_duplicates
            )

    def test_configuration_sources_validation_duplicate_priorities_optional(self):
        """Test that duplicate priorities are allowed for optional sources."""
        # Duplicate priorities in optional sources should be allowed
        sources_with_duplicates = [
            ModelConfigurationSource(source_type="file", priority=10, required=False),
            ModelConfigurationSource(
                source_type="environment",
                priority=10,  # Same priority, but optional
                required=False,
            ),
        ]

        config = ModelConfigurationSubcontract(
            config_name="test", configuration_sources=sources_with_duplicates
        )

        assert len(config.configuration_sources) == 2

    def test_validation_rules_overlapping_keys(self):
        """Test validation that required and optional keys don't overlap."""
        overlapping_validation = ModelConfigurationValidation(
            required_keys=["database_url", "api_key"],
            optional_keys=["api_key", "debug_mode"],  # api_key appears in both
        )

        with pytest.raises(ValidationError, match="both required and optional"):
            ModelConfigurationSubcontract(
                config_name="test", validation_rules=overlapping_validation
            )

    def test_get_effective_environment_prefix(self):
        """Test getting effective environment variable prefix."""
        # With explicit prefix
        config = ModelConfigurationSubcontract(
            config_name="test-config", environment_variable_prefix="EXPLICIT_"
        )
        assert config.get_effective_environment_prefix() == "EXPLICIT_"

        # With inherit_environment=True, should generate from config_name
        config = ModelConfigurationSubcontract(
            config_name="test-config", inherit_environment=True
        )
        assert config.get_effective_environment_prefix() == "TEST_CONFIG_"

        # With inherit_environment=False and no explicit prefix
        config = ModelConfigurationSubcontract(
            config_name="test-config", inherit_environment=False
        )
        assert config.get_effective_environment_prefix() is None

    def test_is_key_sensitive(self):
        """Test checking if configuration key is sensitive."""
        validation = ModelConfigurationValidation(
            sensitive_keys=["api_key", "database_password", "secret_token"]
        )

        config = ModelConfigurationSubcontract(
            config_name="test", validation_rules=validation
        )

        assert config.is_key_sensitive("api_key") is True
        assert config.is_key_sensitive("database_password") is True
        assert config.is_key_sensitive("public_key") is False
        assert config.is_key_sensitive("log_level") is False

    def test_get_required_keys_for_environment(self):
        """Test getting required keys for specific environment."""
        validation = ModelConfigurationValidation(
            required_keys=["database_url", "api_key"],
            environment_specific={
                EnumEnvironment.PRODUCTION: {
                    "ssl_cert": "required",
                    "monitoring_key": "required",
                },
                EnumEnvironment.DEVELOPMENT: {
                    "debug_mode": "optional",
                    "test_db": "required",
                },
            },
        )

        config = ModelConfigurationSubcontract(
            config_name="test",
            target_environment=EnumEnvironment.DEVELOPMENT,
            validation_rules=validation,
        )

        # Default environment (DEVELOPMENT)
        required_keys = config.get_required_keys_for_environment()
        assert set(required_keys) == {"database_url", "api_key", "test_db"}

        # Specific environment (PRODUCTION)
        required_keys = config.get_required_keys_for_environment(
            EnumEnvironment.PRODUCTION
        )
        assert set(required_keys) == {
            "database_url",
            "api_key",
            "ssl_cert",
            "monitoring_key",
        }

    def test_should_reload_on_change(self):
        """Test checking if configuration should reload on source change."""
        # With auto_reload_on_change=False
        config = ModelConfigurationSubcontract(
            config_name="test", auto_reload_on_change=False
        )
        assert config.should_reload_on_change("file") is False

        # With auto_reload_on_change=True but no matching source
        config = ModelConfigurationSubcontract(
            config_name="test",
            auto_reload_on_change=True,
            configuration_sources=[
                ModelConfigurationSource(
                    source_type="database", watch_for_changes=False
                )
            ],
        )
        assert config.should_reload_on_change("file") is False

        # With matching source that has watch_for_changes=True
        config = ModelConfigurationSubcontract(
            config_name="test",
            auto_reload_on_change=True,
            configuration_sources=[
                ModelConfigurationSource(source_type="file", watch_for_changes=True)
            ],
        )
        assert config.should_reload_on_change("file") is True

    def test_get_backup_path(self):
        """Test getting backup path for configuration version."""
        # Without backup directory
        config = ModelConfigurationSubcontract(config_name="test")
        assert config.get_backup_path(1) is None

        # With backup directory
        backup_dir = Path("/var/backups/config")
        config = ModelConfigurationSubcontract(
            config_name="test-config", backup_directory=backup_dir
        )

        backup_path = config.get_backup_path(3)
        expected_path = backup_dir / "test-config-v3.backup"
        assert backup_path == expected_path

    def test_validate_runtime_update_allowed_success(self):
        """Test successful runtime update validation."""
        config = ModelConfigurationSubcontract(
            config_name="test", allow_runtime_updates=True
        )

        # Should not raise an exception
        config.validate_runtime_update_allowed()

    def test_validate_runtime_update_allowed_failure(self):
        """Test runtime update validation failure."""
        config = ModelConfigurationSubcontract(
            config_name="test", allow_runtime_updates=False
        )

        with pytest.raises(OnexError) as exc_info:
            config.validate_runtime_update_allowed()

        assert exc_info.value.error_code == CoreErrorCode.INVALID_OPERATION
        assert "Runtime configuration updates are not allowed" in exc_info.value.message
        # Check for config_name in nested context if necessary
        context_data = exc_info.value.context.get("context", exc_info.value.context)
        assert context_data.get("config_name") == "test"

    def test_create_configuration_source(self):
        """Test creating configuration source through subcontract."""
        config = ModelConfigurationSubcontract(config_name="test")

        source = config.create_configuration_source(
            source_type="file",
            source_path="/path/to/config.yaml",
            priority=25,
            required=True,
            watch_for_changes=True,
        )

        assert isinstance(source, ModelConfigurationSource)
        assert source.source_type == "file"
        assert source.source_path == "/path/to/config.yaml"
        assert source.priority == 25
        assert source.required is True
        assert source.watch_for_changes is True

    def test_add_configuration_source_success(self):
        """Test successfully adding configuration source."""
        config = ModelConfigurationSubcontract(config_name="test")

        source = ModelConfigurationSource(source_type="file", priority=50)

        config.add_configuration_source(source)

        assert len(config.configuration_sources) == 1
        assert config.configuration_sources[0] == source

    def test_add_configuration_source_duplicate_required_priority(self):
        """Test adding configuration source with duplicate required priority."""
        existing_source = ModelConfigurationSource(
            source_type="file", priority=50, required=True
        )

        config = ModelConfigurationSubcontract(
            config_name="test", configuration_sources=[existing_source]
        )

        duplicate_source = ModelConfigurationSource(
            source_type="database", priority=50, required=True  # Same priority
        )

        with pytest.raises(OnexError) as exc_info:
            config.add_configuration_source(duplicate_source)

        assert exc_info.value.error_code == CoreErrorCode.DUPLICATE_REGISTRATION
        assert "priority 50 already exists" in exc_info.value.message

    def test_add_configuration_source_sorting(self):
        """Test that sources are sorted by priority after adding."""
        config = ModelConfigurationSubcontract(config_name="test")

        # Add sources in reverse priority order
        config.add_configuration_source(
            ModelConfigurationSource(source_type="c", priority=100)
        )
        config.add_configuration_source(
            ModelConfigurationSource(source_type="a", priority=10)
        )
        config.add_configuration_source(
            ModelConfigurationSource(source_type="b", priority=50)
        )

        # Should be sorted by priority (lower priority = higher precedence)
        assert config.configuration_sources[0].source_type == "a"  # priority 10
        assert config.configuration_sources[1].source_type == "b"  # priority 50
        assert config.configuration_sources[2].source_type == "c"  # priority 100

    def test_remove_configuration_source_by_type_and_path(self):
        """Test removing configuration source by type and path."""
        sources = [
            ModelConfigurationSource(source_type="file", source_path="/path/a.yaml"),
            ModelConfigurationSource(source_type="file", source_path="/path/b.yaml"),
            ModelConfigurationSource(
                source_type="database", source_path="config_table"
            ),
        ]

        config = ModelConfigurationSubcontract(
            config_name="test", configuration_sources=sources
        )

        # Remove specific source
        removed = config.remove_configuration_source("file", "/path/a.yaml")

        assert removed is True
        assert len(config.configuration_sources) == 2
        assert not any(
            s.source_type == "file" and s.source_path == "/path/a.yaml"
            for s in config.configuration_sources
        )

    def test_remove_configuration_source_by_type_only(self):
        """Test removing all configuration sources of a given type."""
        sources = [
            ModelConfigurationSource(source_type="file", source_path="/path/a.yaml"),
            ModelConfigurationSource(source_type="file", source_path="/path/b.yaml"),
            ModelConfigurationSource(source_type="database"),
        ]

        config = ModelConfigurationSubcontract(
            config_name="test", configuration_sources=sources
        )

        # Remove all file sources
        removed = config.remove_configuration_source("file")

        assert removed is True
        assert len(config.configuration_sources) == 1
        assert config.configuration_sources[0].source_type == "database"

    def test_remove_configuration_source_not_found(self):
        """Test removing non-existent configuration source."""
        config = ModelConfigurationSubcontract(config_name="test")

        removed = config.remove_configuration_source("nonexistent")

        assert removed is False
        assert len(config.configuration_sources) == 0
