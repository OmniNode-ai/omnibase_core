"""
CLI Command Registry

Manages dynamic discovery and registration of CLI commands from node contracts.
This replaces hardcoded command enums with flexible, contract-driven command discovery.
"""

import logging
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.core.model_cli_command_definition import (
    ModelCliCommandDefinition,
)
from omnibase_core.models.core.model_event_type import ModelEventType
from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.models.core.model_node_reference import ModelNodeReference
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

logger = logging.getLogger(__name__)


class ModelCliCommandRegistry(BaseModel):
    """
    Registry for dynamically discovered CLI commands.

    This registry scans node contracts to discover available CLI commands,
    enabling third-party nodes to automatically expose their functionality.
    """

    model_config = ConfigDict(extra="ignore", frozen=False)

    commands: dict[str, ModelCliCommandDefinition] = Field(
        default_factory=dict,
        description="Registered commands by command name",
    )

    commands_by_node: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Command names grouped by node name",
    )

    commands_by_category: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Command names grouped by category",
    )

    discovery_paths: list[Path] = Field(
        default_factory=list,
        description="Paths searched for node contracts",
    )

    def register_command(self, command: ModelCliCommandDefinition) -> None:
        """Register a CLI command definition."""
        command_name = command.command_name
        qualified_name = command.get_qualified_name()

        # Register by both simple and qualified names
        self.commands[command_name] = command
        if qualified_name != command_name:
            self.commands[qualified_name] = command

        # Group by node
        node_name = command.target_node.node_name
        if node_name not in self.commands_by_node:
            self.commands_by_node[node_name] = []
        if command_name not in self.commands_by_node[node_name]:
            self.commands_by_node[node_name].append(command_name)

        # Group by category
        category = command.category
        if category not in self.commands_by_category:
            self.commands_by_category[category] = []
        if command_name not in self.commands_by_category[category]:
            self.commands_by_category[category].append(command_name)

    def get_command(self, command_name: str) -> ModelCliCommandDefinition | None:
        """Get command definition by name (supports qualified names)."""
        return self.commands.get(command_name)

    def get_commands_for_node(self, node_name: str) -> list[ModelCliCommandDefinition]:
        """Get all commands for a specific node."""
        command_names = self.commands_by_node.get(node_name, [])
        return [self.commands[name] for name in command_names if name in self.commands]

    def get_commands_by_category(
        self,
        category: str,
    ) -> list[ModelCliCommandDefinition]:
        """Get all commands in a specific category."""
        command_names = self.commands_by_category.get(category, [])
        return [self.commands[name] for name in command_names if name in self.commands]

    def get_all_commands(self) -> list[ModelCliCommandDefinition]:
        """Get all registered commands."""
        # Return unique commands (avoid duplicates from qualified names)
        seen_commands = set()
        unique_commands = []
        for command in self.commands.values():
            command_id = id(command)
            if command_id not in seen_commands:
                seen_commands.add(command_id)
                unique_commands.append(command)
        return unique_commands

    def get_command_names(self) -> list[str]:
        """Get all registered command names."""
        return list(self.commands.keys())

    def discover_from_contracts(self, base_path: Path | None = None) -> int:
        """
        Discover CLI commands from node contracts.

        Args:
            base_path: Base path to search for nodes (defaults to src/omnibase_core/nodes)

        Returns:
            Number of commands discovered
        """
        if base_path is None:
            # Default to standard ONEX nodes directory
            base_path = Path("src/omnibase_core/nodes")

        if not base_path.exists():
            return 0

        commands_discovered = 0

        # Scan for node directories
        for node_dir in base_path.iterdir():
            if not node_dir.is_dir() or not node_dir.name.startswith("node_"):
                continue

            # Look for versioned directories
            for version_dir in node_dir.iterdir():
                if not version_dir.is_dir() or not version_dir.name.startswith("v"):
                    continue

                contract_path = version_dir / "contract.yaml"
                if contract_path.exists():
                    commands_discovered += self._discover_from_contract_file(
                        contract_path,
                        node_dir.name,
                    )

        return commands_discovered

    def _discover_from_contract_file(self, contract_path: Path, node_name: str) -> int:
        """Discover commands from a single contract file."""
        try:
            # Load and validate YAML using Pydantic model
            contract_model = load_and_validate_yaml_model(
                contract_path, ModelGenericYaml
            )
            contract_data = contract_model.model_dump()

            commands_discovered = 0

            # Check for cli_interface section
            cli_interface = contract_data.get("cli_interface", {})
            if not cli_interface:
                return 0

            commands = cli_interface.get("commands", [])
            for command_data in commands:
                try:
                    command = self._create_command_from_contract(
                        command_data,
                        node_name,
                    )
                    if command:
                        self.register_command(command)
                        commands_discovered += 1
                except (
                    AttributeError,
                    KeyError,
                    RuntimeError,
                    TypeError,
                    ValueError,
                ) as e:
                    # Log error but continue processing other commands
                    logger.debug(
                        "Failed to create command from contract for node '%s': %s",
                        node_name,
                        e,
                    )

            return commands_discovered

        except Exception:  # fallback-ok: resilient discovery, invalid contract shouldn't break entire discovery
            return 0

    def _create_command_from_contract(
        self,
        command_data: Mapping[str, object] | str,
        node_name: str,
    ) -> ModelCliCommandDefinition | None:
        """Create a command definition from contract data."""
        try:
            # Handle both string and object formats
            if isinstance(command_data, str):
                # Simple string format - just the command name
                command_name_str = command_data
                action = command_data
                description = f"Execute {command_data} on {node_name}"
                category = "general"
                event_type_name = "NODE_START"
                examples: list[str] = []
            else:
                # Object format with detailed information
                command_name_raw = command_data.get("command_name") or command_data.get(
                    "name",
                )
                if not command_name_raw:
                    return None

                # Type assertion: we know command_name_raw is truthy and should be str
                command_name_str = str(command_name_raw)
                # Cast values from Mapping[str, object] to expected types
                # Pydantic validates at runtime - these are safe casts for contract data
                action_raw = command_data.get("action", command_name_str)
                action = str(action_raw) if action_raw else command_name_str
                desc_raw = command_data.get("description")
                description = (
                    str(desc_raw)
                    if desc_raw
                    else f"Execute {command_name_str} on {node_name}"
                )
                cat_raw = command_data.get("category", "general")
                category = str(cat_raw) if cat_raw else "general"
                evt_raw = command_data.get("event_type", "NODE_START")
                event_type_name = str(evt_raw) if evt_raw else "NODE_START"
                examples_raw = command_data.get("examples", [])
                examples = list(examples_raw) if isinstance(examples_raw, list) else []

            # Create node reference
            node_ref = ModelNodeReference.create_local(node_name=node_name)

            # Create event type
            from omnibase_core.models.primitives.model_semver import ModelSemVer

            event_type = ModelEventType(
                event_name=event_type_name,
                namespace="onex",
                description=f"Event for {command_name_str} command",
                schema_version=ModelSemVer(major=1, minor=0, patch=0),
            )

            # Parse arguments (simplified for now)
            # Note: Converting to empty lists of ModelArgumentDescription
            # TODO(OMN-TBD): Extract actual argument descriptions from command metadata  [NEEDS TICKET]
            from omnibase_core.models.core.model_argument_description import (
                ModelArgumentDescription,
            )

            required_args: list[ModelArgumentDescription] = []
            optional_args: list[ModelArgumentDescription] = []

            # Create command definition
            return ModelCliCommandDefinition(
                command_name=command_name_str,
                target_node=node_ref,
                action=action,
                description=description,
                required_args=required_args,
                optional_args=optional_args,
                event_type=event_type,
                examples=examples,
                category=category,
            )

        except Exception:  # fallback-ok: malformed command data should return None, caller checks for None
            return None

    def clear(self) -> None:
        """Clear all registered commands."""
        self.commands.clear()
        self.commands_by_node.clear()
        self.commands_by_category.clear()


def get_global_command_registry() -> ModelCliCommandRegistry:
    """Get the CLI command registry from DI container.

    Raises:
        ModelOnexError: If DI container is not initialized
    """
    from omnibase_core.models.container.model_onex_container import (
        get_model_onex_container_sync,
    )

    try:
        container = get_model_onex_container_sync()
        registry: ModelCliCommandRegistry = container.command_registry()
        return registry
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        raise ModelOnexError(
            message="DI container not initialized - cannot get command registry. "
            "Initialize the container first.",
            error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
        ) from e


def discover_commands_from_contracts(base_path: Path | None = None) -> int:
    """Discover commands from contracts and register them globally."""
    registry = get_global_command_registry()
    return registry.discover_from_contracts(base_path)


def get_command_definition(command_name: str) -> ModelCliCommandDefinition | None:
    """Get a command definition by name from the global registry."""
    registry = get_global_command_registry()
    return registry.get_command(command_name)
