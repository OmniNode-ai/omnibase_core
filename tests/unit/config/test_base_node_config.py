#!/usr/bin/env python3
"""
Unit tests for BaseNodeConfig.

Tests the base configuration model for ONEX nodes including validation,
defaults, YAML/JSON support, and error handling.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.config.base_node_config import ModelBaseNodeConfig
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.enums.node import EnumNodeType


class TestModelBaseNodeConfig:
    """Test suite for ModelBaseNodeConfig."""

    def test_minimal_valid_config(self):
        """Test creating config with minimal required fields."""
        config = ModelBaseNodeConfig(node_id="test-node")

        assert config.node_id == "test-node"
        assert config.node_type == EnumNodeType.COMPUTE  # Default
        assert config.log_level == EnumLogLevel.INFO  # Default
        assert config.max_concurrent_operations == 10  # Default

    def test_full_config_creation(self):
        """Test creating config with all fields specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "test.log"

            config = ModelBaseNodeConfig(
                node_id="full-test-node",
                node_name="Full Test Node",
                node_type=EnumNodeType.EFFECT,
                node_version="2.1.0",
                log_level=EnumLogLevel.DEBUG,
                log_to_file=True,
                log_file_path=log_path,
                max_concurrent_operations=50,
                operation_timeout_seconds=45.0,
                debug_mode=True,
                custom_config={"feature_flag": True, "timeout": 30},
                environment_variables=["TEST_VAR", "CONFIG_PATH"],
            )

            assert config.node_id == "full-test-node"
            assert config.node_name == "Full Test Node"
            assert config.node_type == EnumNodeType.EFFECT
            assert config.node_version == "2.1.0"
            assert config.log_level == EnumLogLevel.DEBUG
            assert config.log_to_file is True
            assert config.log_file_path == log_path
            assert config.max_concurrent_operations == 50
            assert config.operation_timeout_seconds == 45.0
            assert config.debug_mode is True
            assert config.custom_config == {"feature_flag": True, "timeout": 30}
            assert config.environment_variables == ["TEST_VAR", "CONFIG_PATH"]

    def test_node_id_validation(self):
        """Test node_id validation rules."""
        # Valid node IDs
        valid_ids = [
            "test-node",
            "test_node",
            "test.node",
            "node123",
            "test-node-123",
            "a",
        ]

        for node_id in valid_ids:
            config = ModelBaseNodeConfig(node_id=node_id)
            assert config.node_id == node_id

        # Invalid node IDs
        invalid_ids = [
            "",  # Empty
            "test node",  # Space
            "test@node",  # Special character
            "test/node",  # Slash
        ]

        for node_id in invalid_ids:
            with pytest.raises(ValidationError):
                ModelBaseNodeConfig(node_id=node_id)

    def test_log_file_path_validation(self):
        """Test log file path validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "test.log"

            # Valid: log_to_file=True with path
            config = ModelBaseNodeConfig(
                node_id="test", log_to_file=True, log_file_path=log_path
            )
            assert config.log_file_path == log_path

            # Valid: log_to_file=False with no path
            config = ModelBaseNodeConfig(node_id="test", log_to_file=False)
            assert config.log_file_path is None

            # Invalid: log_to_file=True with no path
            with pytest.raises(
                ValidationError, match="log_file_path must be specified"
            ):
                ModelBaseNodeConfig(
                    node_id="test", log_to_file=True, log_file_path=None
                )

    def test_initialize_log_directory(self):
        """Test log directory initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "logs" / "test.log"

            config = ModelBaseNodeConfig(
                node_id="test", log_to_file=True, log_file_path=log_path
            )

            # Directory should not exist yet
            assert not log_path.parent.exists()

            # Initialize should create directory
            config.initialize_log_directory()
            assert log_path.parent.exists()

    def test_initialize_log_directory_permission_error(self):
        """Test log directory initialization with permission error."""
        # Use a path that will cause permission error
        restricted_path = Path("/root/restricted/test.log")

        config = ModelBaseNodeConfig(
            node_id="test", log_to_file=True, log_file_path=restricted_path
        )

        with pytest.raises(OnexError) as exc_info:
            config.initialize_log_directory()

        assert exc_info.value.error_code == CoreErrorCode.INVALID_PARAMETER
        assert "Cannot create log file directory" in str(exc_info.value)

    def test_custom_config_validation(self):
        """Test custom config validation."""
        # Valid custom config
        valid_config = {"valid_key": "value", "another_key": 123}
        config = ModelBaseNodeConfig(node_id="test", custom_config=valid_config)
        assert config.custom_config == valid_config

        # Invalid custom config keys
        invalid_configs = [
            {"invalid-key": "value"},  # Hyphen not allowed
            {"123invalid": "value"},  # Can't start with number
            {"invalid key": "value"},  # Space not allowed
        ]

        for invalid_config in invalid_configs:
            with pytest.raises(ValidationError):
                ModelBaseNodeConfig(node_id="test", custom_config=invalid_config)

    def test_custom_config_methods(self):
        """Test custom config getter/setter methods."""
        config = ModelBaseNodeConfig(
            node_id="test", custom_config={"existing_key": "existing_value"}
        )

        # Test getter
        assert config.get_custom_config("existing_key") == "existing_value"
        assert config.get_custom_config("nonexistent_key") is None
        assert config.get_custom_config("nonexistent_key", "default") == "default"

        # Test setter with valid key
        config.set_custom_config("new_key", "new_value")
        assert config.custom_config["new_key"] == "new_value"

        # Test setter with invalid key
        with pytest.raises(OnexError):
            config.set_custom_config("invalid-key", "value")

    def test_environment_validation(self):
        """Test environment variable validation."""
        config = ModelBaseNodeConfig(
            node_id="test", environment_variables=["TEST_VAR", "ANOTHER_VAR"]
        )

        # Mock environment with one missing variable
        with patch.dict(os.environ, {"TEST_VAR": "value"}, clear=True):
            missing = config.validate_environment()
            assert missing == ["ANOTHER_VAR"]

        # Mock environment with all variables present
        with patch.dict(os.environ, {"TEST_VAR": "value", "ANOTHER_VAR": "value2"}):
            missing = config.validate_environment()
            assert missing == []

    def test_production_mode_detection(self):
        """Test production mode detection."""
        # Production mode (default)
        config = ModelBaseNodeConfig(node_id="test")
        assert config.is_production_mode() is True

        # Debug mode
        config = ModelBaseNodeConfig(node_id="test", debug_mode=True)
        assert config.is_production_mode() is False

        # Development mode
        config = ModelBaseNodeConfig(node_id="test", development_mode=True)
        assert config.is_production_mode() is False

    def test_effective_log_level(self):
        """Test effective log level calculation."""
        # Normal mode
        config = ModelBaseNodeConfig(node_id="test", log_level=EnumLogLevel.WARNING)
        assert config.get_effective_log_level() == EnumLogLevel.WARNING

        # Debug mode forces DEBUG level
        config = ModelBaseNodeConfig(
            node_id="test", log_level=EnumLogLevel.ERROR, debug_mode=True
        )
        assert config.get_effective_log_level() == EnumLogLevel.DEBUG

        # Development mode forces INFO level if higher
        config = ModelBaseNodeConfig(
            node_id="test", log_level=EnumLogLevel.ERROR, development_mode=True
        )
        assert config.get_effective_log_level() == EnumLogLevel.INFO

    def test_yaml_support(self):
        """Test YAML serialization and deserialization support."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            log_path = Path(temp_dir) / "test.log"

            # Create original config
            original_config = ModelBaseNodeConfig(
                node_id="yaml-test",
                node_name="YAML Test Node",
                node_type=EnumNodeType.EFFECT,
                log_level=EnumLogLevel.DEBUG,
                log_to_file=True,
                log_file_path=log_path,
                custom_config={"test_key": "test_value"},
            )

            # Save to YAML (use mode='json' to ensure Path objects are serialized as strings)
            yaml_data = yaml.dump(original_config.model_dump(mode="json"))
            config_path.write_text(yaml_data)

            # Load from YAML
            loaded_data = yaml.safe_load(config_path.read_text())
            loaded_config = ModelBaseNodeConfig(**loaded_data)

            # Verify loaded config matches original
            assert loaded_config.node_id == original_config.node_id
            assert loaded_config.node_name == original_config.node_name
            assert loaded_config.node_type == original_config.node_type
            assert loaded_config.log_level == original_config.log_level
            assert loaded_config.custom_config == original_config.custom_config

    def test_json_support(self):
        """Test JSON serialization and deserialization support."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            log_path = Path(temp_dir) / "test.log"

            # Create original config
            original_config = ModelBaseNodeConfig(
                node_id="json-test",
                node_name="JSON Test Node",
                log_to_file=True,
                log_file_path=log_path,
                custom_config={"json_key": "json_value"},
            )

            # Save to JSON
            config_path.write_text(original_config.model_dump_json(indent=2))

            # Load from JSON
            loaded_config = ModelBaseNodeConfig.model_validate_json(
                config_path.read_text()
            )

            # Verify loaded config matches original
            assert loaded_config.node_id == original_config.node_id
            assert loaded_config.node_name == original_config.node_name
            assert loaded_config.custom_config == original_config.custom_config

    def test_validation_constraints(self):
        """Test various field validation constraints."""
        # Test string length constraints
        with pytest.raises(ValidationError):
            ModelBaseNodeConfig(node_id="a" * 256)  # Too long

        # Test numeric constraints
        with pytest.raises(ValidationError):
            ModelBaseNodeConfig(node_id="test", max_concurrent_operations=0)  # Too low

        with pytest.raises(ValidationError):
            ModelBaseNodeConfig(
                node_id="test", max_concurrent_operations=1001
            )  # Too high

        # Test version pattern
        with pytest.raises(ValidationError):
            ModelBaseNodeConfig(node_id="test", node_version="invalid-version")

        # Valid version patterns
        valid_versions = ["1.0.0", "2.1.3", "1.0.0-alpha", "2.0.0-beta.1"]
        for version in valid_versions:
            config = ModelBaseNodeConfig(node_id="test", node_version=version)
            assert config.node_version == version

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = ModelBaseNodeConfig(node_id="test")

        # Check key defaults
        assert config.node_type == EnumNodeType.COMPUTE
        assert config.node_version == "1.0.0"
        assert config.log_level == EnumLogLevel.INFO
        assert config.log_format == "structured"
        assert config.log_to_console is True
        assert config.log_to_file is False
        assert config.max_concurrent_operations == 10
        assert config.operation_timeout_seconds == 30.0
        assert config.enable_metrics is True
        assert config.health_check_enabled is True
        assert config.enable_circuit_breaker is False
        assert config.debug_mode is False
        assert config.development_mode is False
        assert config.enable_profiling is False
        assert config.custom_config == {}
        assert config.environment_variables == []
