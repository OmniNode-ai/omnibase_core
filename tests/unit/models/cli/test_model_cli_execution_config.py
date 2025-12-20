"""
Tests for ModelCliExecutionConfig.

Validates CLI execution configuration model functionality including
validation, serialization, and edge cases.
"""

import pytest

from omnibase_core.enums.enum_output_format import EnumOutputFormat
from omnibase_core.models.cli.model_cli_execution_config import ModelCliExecutionConfig
from omnibase_core.models.cli.model_cli_execution_input_data import (
    ModelCliExecutionInputData,
)


@pytest.mark.unit
class TestModelCliExecutionConfigBasic:
    """Test basic CLI execution configuration functionality."""

    def test_default_configuration(self):
        """Test default execution configuration values."""
        config = ModelCliExecutionConfig()

        assert config.working_directory is None
        assert config.environment_vars == {}
        assert config.is_dry_run is False
        assert config.is_test_execution is False
        assert config.is_debug_enabled is False
        assert config.is_trace_enabled is False
        assert config.is_verbose is False
        assert config.input_data == {}
        assert config.output_format == EnumOutputFormat.TEXT
        assert config.capture_output is True

    def test_custom_configuration(self, tmp_path):
        """Test custom execution configuration."""
        config = ModelCliExecutionConfig(
            working_directory=tmp_path,
            environment_vars={"VAR1": "value1", "VAR2": "value2"},
            is_dry_run=True,
            is_test_execution=True,
            is_debug_enabled=True,
            is_trace_enabled=True,
            is_verbose=True,
            output_format=EnumOutputFormat.JSON,
            capture_output=False,
        )

        assert config.working_directory == tmp_path
        assert config.environment_vars == {"VAR1": "value1", "VAR2": "value2"}
        assert config.is_dry_run is True
        assert config.is_test_execution is True
        assert config.is_debug_enabled is True
        assert config.is_trace_enabled is True
        assert config.is_verbose is True
        assert config.output_format == EnumOutputFormat.JSON
        assert config.capture_output is False


@pytest.mark.unit
class TestModelCliExecutionConfigMethods:
    """Test methods for managing config data."""

    def test_add_input_data(self):
        """Test adding input data."""
        config = ModelCliExecutionConfig()
        input_data = ModelCliExecutionInputData.from_string("test_key", "test_value")

        config.add_input_data("key1", input_data)
        assert "key1" in config.input_data
        assert config.input_data["key1"] == input_data

    def test_get_input_data(self):
        """Test getting input data."""
        config = ModelCliExecutionConfig()
        input_data = ModelCliExecutionInputData.from_string("test_key", "test_value")
        config.input_data["key1"] = input_data

        retrieved = config.get_input_data("key1")
        assert retrieved == input_data

    def test_get_input_data_with_default(self):
        """Test getting input data with default."""
        config = ModelCliExecutionConfig()
        default = ModelCliExecutionInputData.from_string("default_key", "default_value")

        retrieved = config.get_input_data("nonexistent", default)
        assert retrieved == default

    def test_add_environment_var(self):
        """Test adding environment variable."""
        config = ModelCliExecutionConfig()

        config.add_environment_var("KEY1", "value1")
        assert config.environment_vars["KEY1"] == "value1"

    def test_get_environment_var(self):
        """Test getting environment variable."""
        config = ModelCliExecutionConfig()
        config.environment_vars["KEY1"] = "value1"

        value = config.get_environment_var("KEY1")
        assert value == "value1"

    def test_get_environment_var_with_default(self):
        """Test getting environment variable with default."""
        config = ModelCliExecutionConfig()

        value = config.get_environment_var("NONEXISTENT", "default_value")
        assert value == "default_value"

    def test_is_debug_mode_all_disabled(self):
        """Test is_debug_mode when all debug modes disabled."""
        config = ModelCliExecutionConfig(
            is_debug_enabled=False, is_trace_enabled=False, is_verbose=False
        )
        assert config.is_debug_mode() is False

    def test_is_debug_mode_debug_enabled(self):
        """Test is_debug_mode when debug enabled."""
        config = ModelCliExecutionConfig(is_debug_enabled=True)
        assert config.is_debug_mode() is True

    def test_is_debug_mode_trace_enabled(self):
        """Test is_debug_mode when trace enabled."""
        config = ModelCliExecutionConfig(is_trace_enabled=True)
        assert config.is_debug_mode() is True

    def test_is_debug_mode_verbose_enabled(self):
        """Test is_debug_mode when verbose enabled."""
        config = ModelCliExecutionConfig(is_verbose=True)
        assert config.is_debug_mode() is True


@pytest.mark.unit
class TestModelCliExecutionConfigFactoryMethods:
    """Test factory methods for creating configurations."""

    def test_create_production(self):
        """Test production configuration factory."""
        config = ModelCliExecutionConfig.create_production()

        assert config.is_dry_run is False
        assert config.is_test_execution is False
        assert config.is_debug_enabled is False
        assert config.is_trace_enabled is False
        assert config.is_verbose is False

    def test_create_debug(self):
        """Test debug configuration factory."""
        config = ModelCliExecutionConfig.create_debug()

        assert config.is_debug_enabled is True
        assert config.is_trace_enabled is True
        assert config.is_verbose is True

    def test_create_test(self):
        """Test test configuration factory."""
        config = ModelCliExecutionConfig.create_test()

        assert config.is_test_execution is True
        assert config.is_debug_enabled is True
        assert config.is_verbose is True


@pytest.mark.unit
class TestModelCliExecutionConfigProtocols:
    """Test protocol method implementations."""

    def test_serialize(self):
        """Test serialize method (Serializable protocol)."""
        config = ModelCliExecutionConfig(
            is_debug_enabled=True, environment_vars={"KEY": "value"}
        )

        data = config.serialize()

        assert isinstance(data, dict)
        assert "is_debug_enabled" in data
        assert "environment_vars" in data

    def test_get_name(self):
        """Test get_name method (Nameable protocol)."""
        config = ModelCliExecutionConfig()

        name = config.get_name()

        assert "ModelCliExecutionConfig" in name

    def test_set_name(self):
        """Test set_name method (Nameable protocol)."""
        config = ModelCliExecutionConfig()

        # Should not raise exception even if no name field
        config.set_name("test_name")

    def test_validate_instance(self):
        """Test validate_instance method (ProtocolValidatable protocol)."""
        config = ModelCliExecutionConfig()

        result = config.validate_instance()

        assert result is True


@pytest.mark.unit
class TestModelCliExecutionConfigSerialization:
    """Test serialization and deserialization."""

    def test_model_dump(self):
        """Test serialization to dictionary."""
        config = ModelCliExecutionConfig(
            is_debug_enabled=True, environment_vars={"KEY": "VALUE"}
        )

        data = config.model_dump()

        assert data["is_debug_enabled"] is True
        assert data["environment_vars"] == {"KEY": "VALUE"}

    def test_round_trip_serialization(self, tmp_path):
        """Test serialization and deserialization."""
        original = ModelCliExecutionConfig(
            is_dry_run=True,
            working_directory=tmp_path,
            output_format=EnumOutputFormat.YAML,
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelCliExecutionConfig.model_validate(data)

        assert restored.is_dry_run == original.is_dry_run
        assert restored.output_format == original.output_format


@pytest.mark.unit
class TestModelCliExecutionConfigEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_environment_vars(self):
        """Test with empty environment variables dict."""
        config = ModelCliExecutionConfig(environment_vars={})
        assert config.environment_vars == {}

    def test_large_environment_vars(self):
        """Test with many environment variables."""
        env_vars = {f"VAR{i}": f"value{i}" for i in range(100)}
        config = ModelCliExecutionConfig(environment_vars=env_vars)
        assert len(config.environment_vars) == 100

    def test_all_debug_modes_enabled(self):
        """Test with all debug modes enabled."""
        config = ModelCliExecutionConfig(
            is_debug_enabled=True, is_trace_enabled=True, is_verbose=True
        )
        assert config.is_debug_mode() is True

    def test_output_format_enum(self):
        """Test with different output formats."""
        for format_type in EnumOutputFormat:
            config = ModelCliExecutionConfig(output_format=format_type)
            assert config.output_format == format_type
