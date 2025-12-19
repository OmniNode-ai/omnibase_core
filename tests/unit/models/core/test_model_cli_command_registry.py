"""
Tests for ModelCliCommandRegistry - Advanced CLI command registry system.

This module tests dynamic command discovery, registration, and retrieval
from node contracts, supporting third-party extensibility.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from omnibase_core.models.core.model_cli_command_definition import (
    ModelCliCommandDefinition,
)
from omnibase_core.models.core.model_cli_command_registry import (
    ModelCliCommandRegistry,
    discover_commands_from_contracts,
    get_command_definition,
    get_global_command_registry,
)
from omnibase_core.models.core.model_event_type import ModelEventType
from omnibase_core.models.core.model_node_reference import ModelNodeReference
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


@pytest.mark.unit
class TestModelCliCommandRegistryCreation:
    """Test command registry initialization and basic properties."""

    def test_registry_initialization_defaults(self):
        """Test registry initializes with empty collections."""
        registry = ModelCliCommandRegistry()

        assert isinstance(registry.commands, dict)
        assert isinstance(registry.commands_by_node, dict)
        assert isinstance(registry.commands_by_category, dict)
        assert isinstance(registry.discovery_paths, list)
        assert len(registry.commands) == 0
        assert len(registry.commands_by_node) == 0
        assert len(registry.commands_by_category) == 0

    def test_registry_initialization_with_data(self):
        """Test registry initialization with provided data."""
        commands = {"test_cmd": self._create_test_command("test_cmd", "test_node")}
        registry = ModelCliCommandRegistry(
            version=DEFAULT_VERSION,
            commands=commands,
            commands_by_node={"test_node": ["test_cmd"]},
            commands_by_category={"general": ["test_cmd"]},
            discovery_paths=[Path("/test/path")],
        )

        assert len(registry.commands) == 1
        assert "test_cmd" in registry.commands
        assert len(registry.commands_by_node) == 1
        assert len(registry.commands_by_category) == 1
        assert len(registry.discovery_paths) == 1

    def _create_test_command(
        self, command_name: str, node_name: str, category: str = "general"
    ) -> ModelCliCommandDefinition:
        """Helper to create test command definition."""
        return ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name=command_name,
            target_node=ModelNodeReference.create_local(node_name),
            action=command_name,
            description=f"Test command {command_name}",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test event",
            ),
            category=category,
        )


@pytest.mark.unit
class TestCommandRegistration:
    """Test command registration functionality."""

    def test_register_single_command(self):
        """Test registering a single command."""
        registry = ModelCliCommandRegistry()
        command = self._create_test_command("generate", "node_generator")

        registry.register_command(command)

        assert "generate" in registry.commands
        assert registry.commands["generate"] == command
        assert "node_generator" in registry.commands_by_node
        assert "generate" in registry.commands_by_node["node_generator"]
        assert "general" in registry.commands_by_category
        assert "generate" in registry.commands_by_category["general"]

    def test_register_command_with_qualified_name(self):
        """Test command registration creates qualified name mapping."""
        registry = ModelCliCommandRegistry()
        node_ref = ModelNodeReference(
            version=DEFAULT_VERSION,
            node_name="test_node",
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

        registry.register_command(command)

        # Both simple and qualified names should work
        assert "validate" in registry.commands
        assert "third_party:validate" in registry.commands
        assert registry.commands["validate"] == command
        assert registry.commands["third_party:validate"] == command

    def test_register_multiple_commands_same_node(self):
        """Test registering multiple commands for the same node."""
        registry = ModelCliCommandRegistry()
        cmd1 = self._create_test_command("build", "node_builder")
        cmd2 = self._create_test_command("deploy", "node_builder")

        registry.register_command(cmd1)
        registry.register_command(cmd2)

        assert len(registry.commands_by_node["node_builder"]) == 2
        assert "build" in registry.commands_by_node["node_builder"]
        assert "deploy" in registry.commands_by_node["node_builder"]

    def test_register_multiple_commands_same_category(self):
        """Test registering multiple commands in the same category."""
        registry = ModelCliCommandRegistry()
        cmd1 = self._create_test_command("test1", "node1", category="testing")
        cmd2 = self._create_test_command("test2", "node2", category="testing")

        registry.register_command(cmd1)
        registry.register_command(cmd2)

        assert len(registry.commands_by_category["testing"]) == 2
        assert "test1" in registry.commands_by_category["testing"]
        assert "test2" in registry.commands_by_category["testing"]

    def test_register_command_no_duplicates_in_node_list(self):
        """Test that re-registering same command doesn't create duplicates."""
        registry = ModelCliCommandRegistry()
        command = self._create_test_command("process", "node_processor")

        registry.register_command(command)
        registry.register_command(command)

        # Should only appear once in node list
        assert registry.commands_by_node["node_processor"].count("process") == 1

    def test_register_command_no_duplicates_in_category_list(self):
        """Test that re-registering same command doesn't create duplicates."""
        registry = ModelCliCommandRegistry()
        command = self._create_test_command("analyze", "node_analyzer")

        registry.register_command(command)
        registry.register_command(command)

        # Should only appear once in category list
        assert registry.commands_by_category["general"].count("analyze") == 1

    def _create_test_command(
        self, command_name: str, node_name: str, category: str = "general"
    ) -> ModelCliCommandDefinition:
        """Helper to create test command definition."""
        return ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name=command_name,
            target_node=ModelNodeReference.create_local(node_name),
            action=command_name,
            description=f"Test command {command_name}",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test event",
            ),
            category=category,
        )


@pytest.mark.unit
class TestCommandRetrieval:
    """Test command retrieval functionality."""

    def test_get_command_by_simple_name(self):
        """Test retrieving command by simple name."""
        registry = ModelCliCommandRegistry()
        command = self._create_test_command("validate", "node_validator")
        registry.register_command(command)

        result = registry.get_command("validate")

        assert result is not None
        assert result.command_name == "validate"
        assert result == command

    def test_get_command_by_qualified_name(self):
        """Test retrieving command by qualified name."""
        registry = ModelCliCommandRegistry()
        node_ref = ModelNodeReference(
            version=DEFAULT_VERSION,
            node_name="test_node",
            namespace="plugin_ns",
            node_type="plugin",
        )
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="process",
            target_node=node_ref,
            action="process",
            description="Process command",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )
        registry.register_command(command)

        result = registry.get_command("plugin_ns:process")

        assert result is not None
        assert result.command_name == "process"

    def test_get_command_not_found(self):
        """Test retrieving non-existent command returns None."""
        registry = ModelCliCommandRegistry()

        result = registry.get_command("nonexistent")

        assert result is None

    def test_get_commands_for_node(self):
        """Test retrieving all commands for a specific node."""
        registry = ModelCliCommandRegistry()
        cmd1 = self._create_test_command("build", "node_builder")
        cmd2 = self._create_test_command("test", "node_builder")
        cmd3 = self._create_test_command("deploy", "node_deployer")

        registry.register_command(cmd1)
        registry.register_command(cmd2)
        registry.register_command(cmd3)

        results = registry.get_commands_for_node("node_builder")

        assert len(results) == 2
        command_names = [cmd.command_name for cmd in results]
        assert "build" in command_names
        assert "test" in command_names
        assert "deploy" not in command_names

    def test_get_commands_for_node_not_found(self):
        """Test retrieving commands for non-existent node returns empty list."""
        registry = ModelCliCommandRegistry()

        results = registry.get_commands_for_node("nonexistent_node")

        assert results == []

    def test_get_commands_by_category(self):
        """Test retrieving all commands in a category."""
        registry = ModelCliCommandRegistry()
        cmd1 = self._create_test_command("unit_test", "node1", category="testing")
        cmd2 = self._create_test_command(
            "integration_test", "node2", category="testing"
        )
        cmd3 = self._create_test_command("build", "node3", category="build")

        registry.register_command(cmd1)
        registry.register_command(cmd2)
        registry.register_command(cmd3)

        results = registry.get_commands_by_category("testing")

        assert len(results) == 2
        command_names = [cmd.command_name for cmd in results]
        assert "unit_test" in command_names
        assert "integration_test" in command_names
        assert "build" not in command_names

    def test_get_commands_by_category_not_found(self):
        """Test retrieving commands for non-existent category returns empty list."""
        registry = ModelCliCommandRegistry()

        results = registry.get_commands_by_category("nonexistent")

        assert results == []

    def test_get_all_commands(self):
        """Test retrieving all registered commands."""
        registry = ModelCliCommandRegistry()
        cmd1 = self._create_test_command("cmd1", "node1")
        cmd2 = self._create_test_command("cmd2", "node2")
        cmd3 = self._create_test_command("cmd3", "node3")

        registry.register_command(cmd1)
        registry.register_command(cmd2)
        registry.register_command(cmd3)

        results = registry.get_all_commands()

        assert len(results) == 3
        command_names = [cmd.command_name for cmd in results]
        assert "cmd1" in command_names
        assert "cmd2" in command_names
        assert "cmd3" in command_names

    def test_get_all_commands_no_duplicates_with_qualified_names(self):
        """Test get_all_commands doesn't return duplicates for qualified names."""
        registry = ModelCliCommandRegistry()
        node_ref = ModelNodeReference(
            version=DEFAULT_VERSION,
            node_name="test_node",
            namespace="plugin",
            node_type="plugin",
        )
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="action",
            target_node=node_ref,
            action="action",
            description="Test action",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )
        registry.register_command(command)

        results = registry.get_all_commands()

        # Should only return one command, not two (even though both
        # "action" and "plugin:action" are in registry.commands)
        assert len(results) == 1
        assert results[0].command_name == "action"

    def test_get_command_names(self):
        """Test retrieving all command names."""
        registry = ModelCliCommandRegistry()
        node_ref = ModelNodeReference(
            version=DEFAULT_VERSION,
            node_name="test_node",
            namespace="ns",
            node_type="plugin",
        )
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="cmd",
            target_node=node_ref,
            action="cmd",
            description="Test",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )
        registry.register_command(command)

        names = registry.get_command_names()

        # Should include both simple and qualified names
        assert "cmd" in names
        assert "ns:cmd" in names
        assert len(names) == 2

    def _create_test_command(
        self, command_name: str, node_name: str, category: str = "general"
    ) -> ModelCliCommandDefinition:
        """Helper to create test command definition."""
        return ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name=command_name,
            target_node=ModelNodeReference.create_local(node_name),
            action=command_name,
            description=f"Test command {command_name}",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test event",
            ),
            category=category,
        )


@pytest.mark.unit
class TestCommandDiscovery:
    """Test command discovery from contract files."""

    def test_discover_from_contracts_path_not_exists(self):
        """Test discovery returns 0 when path doesn't exist."""
        registry = ModelCliCommandRegistry()

        count = registry.discover_from_contracts(Path("/nonexistent/path"))

        assert count == 0

    @patch("omnibase_core.models.core.model_cli_command_registry.Path.exists")
    @patch("omnibase_core.models.core.model_cli_command_registry.Path.iterdir")
    def test_discover_from_contracts_empty_directory(self, mock_iterdir, mock_exists):
        """Test discovery with empty directory."""
        mock_exists.return_value = True
        mock_iterdir.return_value = []

        registry = ModelCliCommandRegistry()
        count = registry.discover_from_contracts(Path("/test/path"))

        assert count == 0

    @patch("omnibase_core.models.core.model_cli_command_registry.Path.exists")
    @patch("omnibase_core.models.core.model_cli_command_registry.Path.iterdir")
    def test_discover_from_contracts_skips_non_node_dirs(
        self, mock_iterdir, mock_exists
    ):
        """Test discovery skips directories not starting with 'node_'."""
        mock_exists.return_value = True

        # Create mock directories
        invalid_dir = MagicMock()
        invalid_dir.is_dir.return_value = True
        invalid_dir.name = "invalid_dir"

        mock_iterdir.return_value = [invalid_dir]

        registry = ModelCliCommandRegistry()
        count = registry.discover_from_contracts(Path("/test/path"))

        assert count == 0

    def test_discover_from_contract_file_with_valid_yaml(self, tmp_path):
        """Test discovering commands from valid contract YAML."""
        # Create a test contract file
        contract_content = """
cli_interface:
  commands:
    - command_name: test_command
      description: A test command
      category: testing
      event_type: NODE_START
"""
        node_dir = tmp_path / "node_test"
        version_dir = node_dir / "v1"
        version_dir.mkdir(parents=True)

        contract_file = version_dir / "contract.yaml"
        contract_file.write_text(contract_content)

        registry = ModelCliCommandRegistry()
        count = registry._discover_from_contract_file(contract_file, "node_test")

        assert count == 1
        assert "test_command" in registry.commands

    def test_discover_from_contract_file_with_simple_string_format(self, tmp_path):
        """Test discovering commands with simple string format."""
        contract_content = """
cli_interface:
  commands:
    - simple_command
"""
        node_dir = tmp_path / "node_test"
        version_dir = node_dir / "v1"
        version_dir.mkdir(parents=True)

        contract_file = version_dir / "contract.yaml"
        contract_file.write_text(contract_content)

        registry = ModelCliCommandRegistry()
        count = registry._discover_from_contract_file(contract_file, "node_test")

        assert count == 1
        assert "simple_command" in registry.commands
        command = registry.get_command("simple_command")
        assert command is not None
        assert "Execute simple_command on node_test" in command.description

    def test_discover_from_contract_file_invalid_yaml(self, tmp_path):
        """Test discovery handles invalid YAML gracefully."""
        contract_file = tmp_path / "contract.yaml"
        contract_file.write_text("invalid: yaml: content: ::::")

        registry = ModelCliCommandRegistry()
        count = registry._discover_from_contract_file(contract_file, "node_test")

        assert count == 0

    def test_discover_from_contract_file_no_cli_interface(self, tmp_path):
        """Test discovery when contract has no cli_interface section."""
        contract_content = """
node_info:
  name: test_node
  version: 1.0.0
"""
        contract_file = tmp_path / "contract.yaml"
        contract_file.write_text(contract_content)

        registry = ModelCliCommandRegistry()
        count = registry._discover_from_contract_file(contract_file, "node_test")

        assert count == 0

    def test_discover_from_contract_file_empty_commands(self, tmp_path):
        """Test discovery with empty commands list."""
        contract_content = """
cli_interface:
  commands: []
"""
        contract_file = tmp_path / "contract.yaml"
        contract_file.write_text(contract_content)

        registry = ModelCliCommandRegistry()
        count = registry._discover_from_contract_file(contract_file, "node_test")

        assert count == 0

    def test_create_command_from_contract_string_format(self):
        """Test creating command from string format."""
        registry = ModelCliCommandRegistry()

        command = registry._create_command_from_contract("test_cmd", "node_test")

        assert command is not None
        assert command.command_name == "test_cmd"
        assert command.action == "test_cmd"
        assert "node_test" in command.description
        assert command.category == "general"

    def test_create_command_from_contract_dict_format(self):
        """Test creating command from dictionary format."""
        registry = ModelCliCommandRegistry()
        command_data = {
            "command_name": "process",
            "action": "process_data",
            "description": "Process data command",
            "category": "data",
            "event_type": "DATA_PROCESS",
            "examples": ["process --input file.txt"],
        }

        command = registry._create_command_from_contract(command_data, "node_processor")

        assert command is not None
        assert command.command_name == "process"
        assert command.action == "process_data"
        assert command.description == "Process data command"
        assert command.category == "data"
        assert len(command.examples) == 1

    def test_create_command_from_contract_dict_uses_name_fallback(self):
        """Test command creation falls back to 'name' field."""
        registry = ModelCliCommandRegistry()
        command_data = {
            "name": "backup",  # Using 'name' instead of 'command_name'
            "description": "Backup command",
        }

        command = registry._create_command_from_contract(command_data, "node_backup")

        assert command is not None
        assert command.command_name == "backup"

    def test_create_command_from_contract_dict_missing_name(self):
        """Test command creation returns None when name is missing."""
        registry = ModelCliCommandRegistry()
        command_data = {
            "description": "Command without name",
        }

        command = registry._create_command_from_contract(command_data, "node_test")

        assert command is None

    def test_create_command_from_contract_invalid_data_returns_none(self):
        """Test command creation handles invalid data gracefully."""
        registry = ModelCliCommandRegistry()

        command = registry._create_command_from_contract(None, "node_test")

        assert command is None


@pytest.mark.unit
class TestRegistryClear:
    """Test registry clearing functionality."""

    def test_clear_empty_registry(self):
        """Test clearing an empty registry."""
        registry = ModelCliCommandRegistry()

        registry.clear()

        assert len(registry.commands) == 0
        assert len(registry.commands_by_node) == 0
        assert len(registry.commands_by_category) == 0

    def test_clear_populated_registry(self):
        """Test clearing a populated registry."""
        registry = ModelCliCommandRegistry()
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
        registry.register_command(command)

        registry.clear()

        assert len(registry.commands) == 0
        assert len(registry.commands_by_node) == 0
        assert len(registry.commands_by_category) == 0


@pytest.mark.serial
@pytest.mark.unit
class TestGlobalRegistry:
    """Test global registry singleton pattern.

    These tests manipulate the global container context and MUST
    run serially to avoid race conditions with parallel test execution.

    The command registry is now accessed through the DI container only.
    """

    @pytest.fixture(autouse=True)
    def reset_global_registry(self):
        """Reset global registry state before and after each test.

        The new pattern uses ApplicationContext (contextvars), so we reset
        the context variable to ensure a fresh container is created for each test.
        """
        from omnibase_core.context.application_context import _current_container

        # Reset context variable to None (clear any existing container)
        # This ensures a fresh container will be created
        context_token = _current_container.set(None)

        yield

        # Restore original context variable state
        _current_container.reset(context_token)

    def test_get_global_command_registry_creates_instance(self):
        """Test global registry is created on first access via container."""
        from omnibase_core.context.application_context import get_current_container

        # Container should be None after fixture reset
        assert get_current_container() is None

        # Getting the global registry will create a container
        registry = get_global_command_registry()

        assert registry is not None
        assert isinstance(registry, ModelCliCommandRegistry)

        # Container should now be set in context
        assert get_current_container() is not None

    def test_get_global_command_registry_returns_same_instance(self):
        """Test global registry returns same instance on subsequent calls."""
        # Get registry twice - should return same instance
        registry1 = get_global_command_registry()
        registry2 = get_global_command_registry()

        assert registry1 is registry2

    def test_discover_commands_from_contracts_uses_global_registry(self, tmp_path):
        """Test module-level discovery function uses global registry."""
        # Global registry is already reset by the autouse fixture
        # Create test contract
        contract_content = """
cli_interface:
  commands:
    - global_test
"""
        contract_file = tmp_path / "contract.yaml"
        contract_file.write_text(contract_content)

        # Mock the discovery to find our test file
        with patch.object(
            ModelCliCommandRegistry, "discover_from_contracts"
        ) as mock_discover:
            mock_discover.return_value = 1

            count = discover_commands_from_contracts(tmp_path)

            assert mock_discover.called

    def test_get_command_definition_uses_global_registry(self):
        """Test module-level get command function uses global registry."""
        # Global registry is already reset by the autouse fixture
        # Register a test command
        registry = get_global_command_registry()
        command = ModelCliCommandDefinition(
            version=DEFAULT_VERSION,
            command_name="global_cmd",
            target_node=ModelNodeReference.create_local("test_node"),
            action="global_cmd",
            description="Global command test",
            event_type=ModelEventType(
                schema_version=DEFAULT_VERSION,
                event_name="NODE_START",
                namespace="onex",
                description="Test",
            ),
        )
        registry.register_command(command)

        # Retrieve via module function
        result = get_command_definition("global_cmd")

        assert result is not None
        assert result.command_name == "global_cmd"
