"""
Tests for ModelCliCommandDefinition - Advanced CLI command definition.

This module tests command definition structure, help text generation,
and command matching for dynamically discovered CLI commands.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_argument_type import EnumArgumentType
from omnibase_core.models.core.model_argument_description import (
    ModelArgumentDescription,
)
from omnibase_core.models.core.model_cli_command_definition import (
    ModelCliCommandDefinition,
)
from omnibase_core.models.core.model_event_type import ModelEventType
from omnibase_core.models.core.model_node_reference import ModelNodeReference
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class TestModelCliCommandDefinitionCreation:
    """Test command definition creation and validation."""

    def test_command_definition_creation_minimal(self):
        """Test creating command definition with minimal required fields."""
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="test",
            target_node=ModelNodeReference.create_local("test_node"),
            action="test_action",
            description="Test command",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test event",
            ),
        )

        assert command.command_name == "test"
        assert command.target_node.node_name == "test_node"
        assert command.action == "test_action"
        assert command.description == "Test command"
        assert command.category == "general"
        assert command.deprecated is False
        assert command.deprecation_message is None
        assert len(command.required_args) == 0
        assert len(command.optional_args) == 0
        assert len(command.examples) == 0

    def test_command_definition_creation_full(self):
        """Test creating command definition with all fields."""
        required_arg = ModelArgumentDescription(
            version=DEFAULT_VERSION,
            name="input",
            description="Input file",
            type=EnumArgumentType.STRING,
            required=True,
        )
        optional_arg = ModelArgumentDescription(
            version=DEFAULT_VERSION,
            name="output",
            description="Output file",
            type=EnumArgumentType.STRING,
            required=False,
            default_value="output.txt",
        )

        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="process",
            target_node=ModelNodeReference.create_local("processor_node"),
            action="process_data",
            description="Process data files",
            required_args=[required_arg],
            optional_args=[optional_arg],
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="DATA_PROCESS",
                namespace="onex",
                description="Data processing event",
            ),
            examples=[
                "process --input data.txt",
                "process --input data.txt --output result.txt",
            ],
            category="data",
            deprecated=True,
            deprecation_message="Use 'process_v2' instead",
        )

        assert command.command_name == "process"
        assert command.category == "data"
        assert command.deprecated is True
        assert command.deprecation_message == "Use 'process_v2' instead"
        assert len(command.required_args) == 1
        assert len(command.optional_args) == 1
        assert len(command.examples) == 2

    def test_command_name_validation_lowercase_start(self):
        """Test command name must start with lowercase letter."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCliCommandDefinition(
                version=DEFAULT_VERSION,
                command_name="Test",  # Invalid - starts with uppercase
                target_node=ModelNodeReference.create_local("test_node"),
                action="test",
                description="Test",
                event_type=ModelEventType(
                    schema_version=DEFAULT_VERSION,
                    event_name="NODE_START",
                    namespace="onex",
                    description="Test",
                ),
            )

        assert "command_name" in str(exc_info.value)

    def test_command_name_validation_pattern(self):
        """Test command name pattern validation."""
        with pytest.raises(ValidationError):
            ModelCliCommandDefinition(
                version=DEFAULT_VERSION,
                command_name="test command",  # Invalid - contains space
                target_node=ModelNodeReference.create_local("test_node"),
                action="test",
                description="Test",
                event_type=ModelEventType(
                    schema_version=DEFAULT_VERSION,
                    event_name="NODE_START",
                    namespace="onex",
                    description="Test",
                ),
            )

    def test_command_name_allows_hyphens_and_underscores(self):
        """Test command name allows hyphens and underscores."""
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="test-command_name",
            target_node=ModelNodeReference.create_local("test_node"),
            action="test",
            description="Test",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )

        assert command.command_name == "test-command_name"

    def test_category_validation_pattern(self):
        """Test category pattern validation."""
        with pytest.raises(ValidationError):
            ModelCliCommandDefinition(
                version=DEFAULT_VERSION,
                command_name="test",
                target_node=ModelNodeReference.create_local("test_node"),
                action="test",
                description="Test",
                event_type=ModelEventType(
                    schema_version=DEFAULT_VERSION,
                    event_name="NODE_START",
                    namespace="onex",
                    description="Test",
                ),
                category="Invalid Category",  # Invalid - contains space and uppercase
            )

    def test_category_allows_underscores(self):
        """Test category allows underscores."""
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="test",
            target_node=ModelNodeReference.create_local("test_node"),
            action="test",
            description="Test",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
            category="test_category",
        )

        assert command.category == "test_category"


class TestQualifiedName:
    """Test qualified name generation."""

    def test_get_qualified_name_local_node(self):
        """Test qualified name for local node without namespace."""
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="build",
            target_node=ModelNodeReference.create_local("builder_node"),
            action="build",
            description="Build command",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )

        qualified_name = command.get_qualified_name()

        assert qualified_name == "build"

    def test_get_qualified_name_with_namespace(self):
        """Test qualified name includes namespace."""
        node_ref = ModelNodeReference(
            version=DEFAULT_VERSION,
            node_name="validator_node",
            namespace="third_party",
            node_type="plugin",
        )
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="validate",
            target_node=node_ref,
            action="validate",
            description="Validation command",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )

        qualified_name = command.get_qualified_name()

        assert qualified_name == "third_party:validate"

    def test_get_qualified_name_empty_namespace(self):
        """Test qualified name when namespace is empty string."""
        node_ref = ModelNodeReference(
            version=DEFAULT_VERSION,
            node_name="test_node",
            namespace="",
            node_type="local",
        )
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="test",
            target_node=node_ref,
            action="test",
            description="Test",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )

        qualified_name = command.get_qualified_name()

        assert qualified_name == "test"


class TestHelpTextGeneration:
    """Test help text generation."""

    def test_get_help_text_basic(self):
        """Test basic help text generation."""
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="simple",
            target_node=ModelNodeReference.create_local("test_node"),
            action="simple",
            description="A simple command",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )

        help_text = command.get_help_text()

        assert "A simple command" in help_text
        assert "Required arguments:" not in help_text
        assert "Optional arguments:" not in help_text
        assert "Examples:" not in help_text

    def test_get_help_text_with_required_args(self):
        """Test help text includes required arguments."""
        required_arg = ModelArgumentDescription(
            version=DEFAULT_VERSION,
            name="input_file",
            description="Path to input file",
            type=EnumArgumentType.STRING,
            required=True,
        )
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="process",
            target_node=ModelNodeReference.create_local("processor"),
            action="process",
            description="Process files",
            required_args=[required_arg],
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )

        help_text = command.get_help_text()

        assert "Required arguments:" in help_text
        assert "--input_file:" in help_text
        assert "Path to input file" in help_text

    def test_get_help_text_with_optional_args(self):
        """Test help text includes optional arguments."""
        optional_arg = ModelArgumentDescription(
            version=DEFAULT_VERSION,
            name="verbose",
            description="Enable verbose output",
            type=EnumArgumentType.BOOLEAN,
            required=False,
            default_value=False,
        )
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="run",
            target_node=ModelNodeReference.create_local("runner"),
            action="run",
            description="Run task",
            optional_args=[optional_arg],
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )

        help_text = command.get_help_text()

        assert "Optional arguments:" in help_text
        assert "--verbose:" in help_text
        assert "Enable verbose output" in help_text
        assert "(default: False)" in help_text

    def test_get_help_text_with_examples(self):
        """Test help text includes examples."""
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="deploy",
            target_node=ModelNodeReference.create_local("deployer"),
            action="deploy",
            description="Deploy application",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
            examples=[
                "deploy --env production",
                "deploy --env staging --dry-run",
            ],
        )

        help_text = command.get_help_text()

        assert "Examples:" in help_text
        assert "deploy --env production" in help_text
        assert "deploy --env staging --dry-run" in help_text

    def test_get_help_text_deprecated_command(self):
        """Test help text for deprecated command."""
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="old_command",
            target_node=ModelNodeReference.create_local("test_node"),
            action="old",
            description="Old command functionality",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
            deprecated=True,
            deprecation_message="Please use 'new_command' instead",
        )

        help_text = command.get_help_text()

        assert "[DEPRECATED]" in help_text
        assert "Please use 'new_command' instead" in help_text
        # Deprecation message should appear before description
        assert help_text.index("[DEPRECATED]") < help_text.index(
            "Old command functionality"
        )

    def test_get_help_text_deprecated_without_message(self):
        """Test help text for deprecated command without custom message."""
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="legacy",
            target_node=ModelNodeReference.create_local("test_node"),
            action="legacy",
            description="Legacy command",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
            deprecated=True,
        )

        help_text = command.get_help_text()

        assert "[DEPRECATED]" in help_text
        assert "This command is deprecated" in help_text

    def test_get_help_text_comprehensive(self):
        """Test comprehensive help text with all elements."""
        required_arg = ModelArgumentDescription(
            version=DEFAULT_VERSION,
            name="source",
            description="Source path",
            type=EnumArgumentType.STRING,
            required=True,
        )
        optional_arg = ModelArgumentDescription(
            version=DEFAULT_VERSION,
            name="destination",
            description="Destination path",
            type=EnumArgumentType.STRING,
            required=False,
            default_value="./output",
        )
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="copy",
            target_node=ModelNodeReference.create_local("copier"),
            action="copy",
            description="Copy files from source to destination",
            required_args=[required_arg],
            optional_args=[optional_arg],
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
            examples=[
                "copy --source /data",
                "copy --source /data --destination /backup",
            ],
            deprecated=True,
            deprecation_message="Use 'rsync' command instead",
        )

        help_text = command.get_help_text()

        # Should contain all sections in order
        assert "[DEPRECATED]" in help_text
        assert "Copy files from source to destination" in help_text
        assert "Required arguments:" in help_text
        assert "--source:" in help_text
        assert "Optional arguments:" in help_text
        assert "--destination:" in help_text
        assert "(default: ./output)" in help_text
        assert "Examples:" in help_text
        assert "copy --source /data" in help_text


class TestCommandMatching:
    """Test command matching functionality."""

    def test_matches_command_simple_name(self):
        """Test matching by simple command name."""
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="test",
            target_node=ModelNodeReference.create_local("test_node"),
            action="test",
            description="Test",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )

        assert command.matches_command("test") is True
        assert command.matches_command("other") is False

    def test_matches_command_qualified_name(self):
        """Test matching by qualified name."""
        node_ref = ModelNodeReference(
            version=DEFAULT_VERSION,
            node_name="validator",
            namespace="plugin",
            node_type="plugin",
        )
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="validate",
            target_node=node_ref,
            action="validate",
            description="Validate",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )

        assert command.matches_command("validate") is True
        assert command.matches_command("plugin:validate") is True
        assert command.matches_command("other:validate") is False

    def test_matches_command_case_sensitive(self):
        """Test command matching is case sensitive."""
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="test",
            target_node=ModelNodeReference.create_local("test_node"),
            action="test",
            description="Test",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )

        assert command.matches_command("test") is True
        assert command.matches_command("Test") is False
        assert command.matches_command("TEST") is False


class TestCommandDefinitionIntegration:
    """Test command definition integration scenarios."""

    def test_command_with_multiple_required_args(self):
        """Test command with multiple required arguments."""
        args = [
            ModelArgumentDescription(
                version=DEFAULT_VERSION,
                name="input",
                description="Input",
                type=EnumArgumentType.STRING,
                required=True,
            ),
            ModelArgumentDescription(
                version=DEFAULT_VERSION,
                name="config",
                description="Config",
                type=EnumArgumentType.STRING,
                required=True,
            ),
            ModelArgumentDescription(
                version=DEFAULT_VERSION,
                name="format",
                description="Format",
                type=EnumArgumentType.STRING,
                required=True,
            ),
        ]
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="convert",
            target_node=ModelNodeReference.create_local("converter"),
            action="convert",
            description="Convert files",
            required_args=args,
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )

        assert len(command.required_args) == 3
        help_text = command.get_help_text()
        assert "--input:" in help_text
        assert "--config:" in help_text
        assert "--format:" in help_text

    def test_command_with_multiple_optional_args(self):
        """Test command with multiple optional arguments."""
        args = [
            ModelArgumentDescription(
                version=DEFAULT_VERSION,
                name="verbose",
                description="Verbose",
                type=EnumArgumentType.BOOLEAN,
                required=False,
                default_value=False,
            ),
            ModelArgumentDescription(
                version=DEFAULT_VERSION,
                name="timeout",
                description="Timeout",
                type=EnumArgumentType.INTEGER,
                required=False,
                default_value=30,
            ),
        ]
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="execute",
            target_node=ModelNodeReference.create_local("executor"),
            action="execute",
            description="Execute task",
            optional_args=args,
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )

        assert len(command.optional_args) == 2
        help_text = command.get_help_text()
        assert "(default: False)" in help_text
        assert "(default: 30)" in help_text

    def test_command_serialization_deserialization(self):
        """Test command can be serialized and deserialized."""
        original = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="serialize_test",
            target_node=ModelNodeReference.create_local("test_node"),
            action="test",
            description="Serialization test",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
            category="testing",
            examples=["serialize_test --help"],
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize from dict
        restored = ModelCliCommandDefinition.model_validate(data)

        assert restored.command_name == original.command_name
        assert restored.action == original.action
        assert restored.description == original.description
        assert restored.category == original.category
        assert restored.examples == original.examples
