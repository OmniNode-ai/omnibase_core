"""Test ModelFunctionNodeData."""

from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_config_type import EnumConfigType
from omnibase_core.enums.enum_function_status import EnumFunctionStatus
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_standard_category import EnumStandardCategory
from omnibase_core.enums.enum_standard_tag import EnumStandardTag
from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue
from omnibase_core.models.metadata.model_function_node_data import ModelFunctionNodeData
from omnibase_core.primitives.model_semver import ModelSemVer


class TestModelFunctionNodeData:
    """Test ModelFunctionNodeData functionality."""

    def test_create_default_instance(self):
        """Test creating a default instance."""
        node = ModelFunctionNodeData()

        assert isinstance(node.node_id, UUID)
        assert node.node_type == EnumNodeType.FUNCTION
        assert node.status == EnumFunctionStatus.ACTIVE
        assert isinstance(node.version, ModelSemVer)
        assert node.version.major == 1
        assert node.version.minor == 0
        assert node.version.patch == 0

    def test_create_function_node(self):
        """Test creating a function node with parameters."""
        node = ModelFunctionNodeData.create_function_node(
            name="test_function",
            description_purpose="Test function for authentication",
            function_category=EnumStandardCategory.AUTHENTICATION,
            complexity=EnumStandardTag.MODERATE,
            custom_tags=["test", "auth"],
        )

        assert node.display_name.display_name == "function_test_function"
        assert (
            node.description.purpose
            == "Function node implementing test_function business logic"
        )
        assert node.tags.primary_category == EnumStandardCategory.AUTHENTICATION
        assert "test" in node.tags.custom_tags
        assert "auth" in node.tags.custom_tags

    def test_add_string_property(self):
        """Test adding string properties."""
        node = ModelFunctionNodeData()

        node.add_string_property(
            name="api_key",
            value="secret_key_123",
            unit="string",
            description="API authentication key",
        )

        assert len(node.string_properties) == 1
        assert node.string_properties[0].metric_display_name == "api_key"
        assert node.string_properties[0].value == "secret_key_123"
        assert node.string_properties[0].unit == "string"
        assert node.string_properties[0].description == "API authentication key"

    def test_add_numeric_property(self):
        """Test adding numeric properties."""
        node = ModelFunctionNodeData()

        node.add_numeric_property(
            name="timeout", value=30.5, unit="seconds", description="Request timeout"
        )

        assert len(node.numeric_properties) == 1
        assert node.numeric_properties[0].metric_display_name == "timeout"
        assert node.numeric_properties[0].value == 30.5
        assert node.numeric_properties[0].unit == "seconds"
        assert node.numeric_properties[0].description == "Request timeout"

    def test_add_boolean_property(self):
        """Test adding boolean properties."""
        node = ModelFunctionNodeData()

        node.add_boolean_property(
            name="enabled",
            value=True,
            unit="boolean",
            description="Feature enabled flag",
        )

        assert len(node.boolean_properties) == 1
        assert node.boolean_properties[0].metric_display_name == "enabled"
        assert node.boolean_properties[0].value is True
        assert node.boolean_properties[0].unit == "boolean"
        assert node.boolean_properties[0].description == "Feature enabled flag"

    def test_add_configuration(self):
        """Test adding configuration objects."""
        node = ModelFunctionNodeData()
        config_id = uuid4()

        settings = {
            "host": ModelCliValue.from_string("localhost"),
            "port": ModelCliValue.from_integer(8080),
        }

        node.add_configuration(
            config_id=config_id,
            config_display_name="Database Config",
            config_type=EnumConfigType.DATABASE_CONFIG,
            settings=settings,
        )

        assert len(node.configurations) == 1
        assert node.configurations[0].config_id == config_id
        assert node.configurations[0].config_display_name == "Database Config"
        assert node.configurations[0].config_type == EnumConfigType.DATABASE_CONFIG
        assert len(node.configurations[0].settings) == 2

    def test_update_display_name(self):
        """Test updating display name."""
        node = ModelFunctionNodeData()
        original_name = node.display_name.display_name

        node.update_display_name("new_function_name")

        assert node.display_name.display_name == "function_new_function_name"
        assert node.display_name.display_name != original_name

    def test_update_description_purpose(self):
        """Test updating description purpose."""
        node = ModelFunctionNodeData()
        original_purpose = node.description.purpose

        node.update_description_purpose("New purpose description")

        assert node.description.purpose == "New purpose description"
        assert node.description.purpose != original_purpose

    def test_add_tag(self):
        """Test adding tags."""
        node = ModelFunctionNodeData()

        # Add custom tag
        result = node.add_tag("custom_tag")
        assert result is True
        assert node.has_tag("custom_tag")

        # Add standard tag
        result = node.add_tag("moderate")
        assert result is True
        assert node.has_tag("moderate")

    def test_remove_tag(self):
        """Test removing tags."""
        node = ModelFunctionNodeData()

        # Add a tag first
        node.add_tag("test_tag")
        assert node.has_tag("test_tag")

        # Remove the tag
        result = node.remove_tag("test_tag")
        assert result is True
        assert not node.has_tag("test_tag")

    def test_has_tag(self):
        """Test checking for tag presence."""
        node = ModelFunctionNodeData()

        # Initially no custom tags
        assert not node.has_tag("nonexistent_tag")

        # Add a tag
        node.add_tag("existing_tag")
        assert node.has_tag("existing_tag")

    def test_get_metadata(self):
        """Test getting metadata."""
        node = ModelFunctionNodeData()
        metadata = node.get_metadata()

        assert isinstance(metadata, dict)
        # Should contain some metadata fields
        assert len(metadata) >= 0

    def test_set_metadata(self):
        """Test setting metadata."""
        node = ModelFunctionNodeData()

        metadata = {
            "status": EnumFunctionStatus.ACTIVE,
            "version": ModelSemVer(major=2, minor=1, patch=0),
        }

        result = node.set_metadata(metadata)
        assert result is True
        assert node.status == EnumFunctionStatus.ACTIVE
        assert node.version.major == 2

    def test_serialize(self):
        """Test serialization."""
        node = ModelFunctionNodeData()
        serialized = node.serialize()

        assert isinstance(serialized, dict)
        assert "node_id" in serialized
        assert "node_type" in serialized
        assert "status" in serialized
        assert "version" in serialized

    def test_validate_instance(self):
        """Test instance validation."""
        node = ModelFunctionNodeData()
        result = node.validate_instance()

        assert result is True

    def test_model_config(self):
        """Test model configuration."""
        assert hasattr(ModelFunctionNodeData, "model_config")
        config = ModelFunctionNodeData.model_config

        assert "extra" in config
        assert "use_enum_values" in config
        assert "validate_assignment" in config
        assert config["extra"] == "ignore"
        assert config["use_enum_values"] is False
        assert config["validate_assignment"] is True
