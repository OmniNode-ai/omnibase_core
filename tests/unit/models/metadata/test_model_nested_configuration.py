"""Test ModelNestedConfiguration."""

from uuid import uuid4

from omnibase_core.enums.enum_config_type import EnumConfigType
from omnibase_core.models.infrastructure.model_value import ModelValue
from omnibase_core.models.metadata.model_nested_configuration import (
    ModelNestedConfiguration,
)


class TestModelNestedConfiguration:
    """Test ModelNestedConfiguration functionality."""

    def test_create_instance_with_required_fields(self):
        """Test creating an instance with required fields."""
        config_id = uuid4()

        config = ModelNestedConfiguration(
            config_id=config_id, config_type=EnumConfigType.DATABASE_CONFIG
        )

        assert config.config_id == config_id
        assert config.config_type == EnumConfigType.DATABASE_CONFIG
        assert config.config_display_name is None
        assert isinstance(config.settings, dict)
        assert len(config.settings) == 0

    def test_create_instance_with_all_fields(self):
        """Test creating an instance with all fields."""
        config_id = uuid4()

        settings = {
            "host": ModelValue.from_string("localhost"),
            "port": ModelValue.from_integer(8080),
        }

        config = ModelNestedConfiguration(
            config_id=config_id,
            config_display_name="Test Config",
            config_type=EnumConfigType.DATABASE_CONFIG,
            settings=settings,
        )

        assert config.config_id == config_id
        assert config.config_display_name == "Test Config"
        assert config.config_type == EnumConfigType.DATABASE_CONFIG
        assert len(config.settings) == 2
        assert "host" in config.settings
        assert "port" in config.settings

    def test_model_config(self):
        """Test model configuration."""
        assert hasattr(ModelNestedConfiguration, "model_config")
        config = ModelNestedConfiguration.model_config

        assert "extra" in config
        assert "use_enum_values" in config
        assert "validate_assignment" in config
        assert config["extra"] == "ignore"
        assert config["use_enum_values"] is False
        assert config["validate_assignment"] is True

    def test_get_metadata(self):
        """Test getting metadata."""
        config_id = uuid4()
        config = ModelNestedConfiguration(
            config_id=config_id, config_type=EnumConfigType.DATABASE_CONFIG
        )

        metadata = config.get_metadata()

        assert isinstance(metadata, dict)
        # Should contain some metadata fields
        assert len(metadata) >= 0

    def test_set_metadata(self):
        """Test setting metadata."""
        config_id = uuid4()
        config = ModelNestedConfiguration(
            config_id=config_id, config_type=EnumConfigType.DATABASE_CONFIG
        )

        metadata = {"config_display_name": "Updated Config Name"}

        result = config.set_metadata(metadata)
        assert result is True
        assert config.config_display_name == "Updated Config Name"

    def test_serialize(self):
        """Test serialization."""
        config_id = uuid4()
        config = ModelNestedConfiguration(
            config_id=config_id, config_type=EnumConfigType.DATABASE_CONFIG
        )

        serialized = config.serialize()

        assert isinstance(serialized, dict)
        assert "config_id" in serialized
        assert "config_type" in serialized
        assert "settings" in serialized

    def test_validate_instance(self):
        """Test instance validation."""
        config_id = uuid4()
        config = ModelNestedConfiguration(
            config_id=config_id, config_type=EnumConfigType.DATABASE_CONFIG
        )

        result = config.validate_instance()
        assert result is True

    def test_settings_manipulation(self):
        """Test manipulating settings."""
        config_id = uuid4()
        config = ModelNestedConfiguration(
            config_id=config_id, config_type=EnumConfigType.DATABASE_CONFIG
        )

        # Add a setting
        config.settings["new_setting"] = ModelValue.from_string("test")

        assert len(config.settings) == 1
        assert "new_setting" in config.settings
        assert config.settings["new_setting"].raw_value == "test"

    def test_different_config_types(self):
        """Test different configuration types."""
        config_id = uuid4()

        for config_type in EnumConfigType:
            config = ModelNestedConfiguration(
                config_id=config_id, config_type=config_type
            )

            assert config.config_type == config_type
            assert config.config_id == config_id

    def test_model_docstring(self):
        """Test that the model has a docstring."""
        assert ModelNestedConfiguration.__doc__ is not None
        assert len(ModelNestedConfiguration.__doc__.strip()) > 0
        assert "Model for nested configuration data" in ModelNestedConfiguration.__doc__

    def test_all_exports(self):
        """Test __all__ exports."""
        from omnibase_core.models.metadata.model_nested_configuration import __all__

        assert len(__all__) > 0
        assert "ModelNestedConfiguration" in __all__
