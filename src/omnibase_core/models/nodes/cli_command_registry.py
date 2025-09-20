"""
CLI Command Registry.

Registry pattern for mapping CLI actions to command implementations,
providing type-safe command dispatch and factory patterns.
"""

from typing import Dict, Type

from omnibase_core.enums.enum_cli_action import EnumCliAction
from omnibase_core.models.nodes.cli_command_base import CliCommand
from omnibase_core.models.nodes.cli_command_execute_node import ExecuteNodeCommand
from omnibase_core.models.nodes.cli_command_get_active_nodes import GetActiveNodesCommand
from omnibase_core.models.nodes.cli_command_list_nodes import ListNodesCommand
from omnibase_core.models.nodes.cli_command_node_info import NodeInfoCommand
from omnibase_core.models.nodes.cli_command_system_info import SystemInfoCommand
from omnibase_core.models.nodes.model_cli_command_result import ModelCliCommandResult
from omnibase_core.models.nodes.model_cli_node_execution_input import (
    ModelCliNodeExecutionInput,
)


class CliCommandRegistry:
    """
    Registry for CLI command implementations.

    Provides command factory and dispatch functionality to replace
    large if/elif chains with maintainable registry patterns.
    """

    def __init__(self) -> None:
        """Initialize command registry."""
        self._command_classes: Dict[EnumCliAction, Type[CliCommand]] = {}
        self._command_instances: Dict[EnumCliAction, CliCommand] = {}
        self._initialize_default_commands()

    def register_command(
        self, action: EnumCliAction, command_class: Type[CliCommand]
    ) -> None:
        """
        Register a command class for an action.

        Args:
            action: CLI action enum
            command_class: Command implementation class
        """
        self._command_classes[action] = command_class
        # Clear cached instance if exists
        if action in self._command_instances:
            del self._command_instances[action]

    def get_command(self, action: EnumCliAction) -> CliCommand | None:
        """
        Get command instance for the given action.

        Args:
            action: CLI action enum

        Returns:
            Command instance or None if not registered
        """
        # Return cached instance if available
        if action in self._command_instances:
            return self._command_instances[action]

        # Create new instance if class is registered
        command_class = self._command_classes.get(action)
        if command_class:
            command_instance = command_class(action)
            self._command_instances[action] = command_instance
            return command_instance

        return None

    async def execute_command(
        self, input_data: ModelCliNodeExecutionInput
    ) -> ModelCliCommandResult:
        """
        Execute command based on input action.

        Args:
            input_data: CLI execution input

        Returns:
            Command execution result
        """
        try:
            # Convert string action to enum
            action_enum = self._get_action_enum(input_data.action)
            if not action_enum:
                return ModelCliCommandResult.error_result(
                    f"Unknown action: {input_data.action}"
                )

            # Get command for action
            command = self.get_command(action_enum)
            if not command:
                return ModelCliCommandResult.error_result(
                    f"No command registered for action: {action_enum.value}"
                )

            # Execute command
            return await command.execute(input_data)

        except Exception as e:
            return ModelCliCommandResult.error_result(
                f"Command execution failed: {str(e)}"
            )

    def get_registered_actions(self) -> list[EnumCliAction]:
        """
        Get list of registered action enums.

        Returns:
            List of registered CLI actions
        """
        return list(self._command_classes.keys())

    def get_registered_action_names(self) -> list[str]:
        """
        Get list of registered action names.

        Returns:
            List of registered action string values
        """
        return [action.value for action in self._command_classes.keys()]

    def is_action_supported(self, action: str | EnumCliAction) -> bool:
        """
        Check if an action is supported.

        Args:
            action: Action string or enum

        Returns:
            True if action is supported
        """
        if isinstance(action, str):
            action_enum = self._get_action_enum(action)
            result = action_enum is not None and action_enum in self._command_classes
        else:
            result = action in self._command_classes  # type: ignore[unreachable]
        return result

    def _get_action_enum(self, action_str: str) -> EnumCliAction | None:
        """
        Convert action string to enum.

        Args:
            action_str: Action string value

        Returns:
            Action enum or None if not found
        """
        try:
            return EnumCliAction(action_str)
        except ValueError:
            return None

    def _initialize_default_commands(self) -> None:
        """Initialize default command mappings."""
        self.register_command(EnumCliAction.LIST_NODES, ListNodesCommand)
        self.register_command(EnumCliAction.GET_ACTIVE_NODES, GetActiveNodesCommand)
        self.register_command(EnumCliAction.EXECUTE_NODE, ExecuteNodeCommand)
        self.register_command(EnumCliAction.NODE_INFO, NodeInfoCommand)
        self.register_command(EnumCliAction.SYSTEM_INFO, SystemInfoCommand)

    def get_command_info(self, action: EnumCliAction) -> Dict[str, str] | None:
        """
        Get information about a registered command.

        Args:
            action: CLI action enum

        Returns:
            Command information dictionary or None
        """
        command = self.get_command(action)
        if not command:
            return None

        return {
            "action": action.value,
            "command_name": command.command_name,
            "command_class": command.__class__.__name__,
        }

    def clear_cache(self) -> None:
        """Clear cached command instances."""
        self._command_instances.clear()

    def reset_to_defaults(self) -> None:
        """Reset registry to default commands only."""
        self._command_classes.clear()
        self._command_instances.clear()
        self._initialize_default_commands()


# Global registry instance
_default_registry = CliCommandRegistry()


def get_default_command_registry() -> CliCommandRegistry:
    """
    Get the default command registry instance.

    Returns:
        Default command registry
    """
    return _default_registry


# Export for use
__all__ = [
    "CliCommandRegistry",
    "get_default_command_registry",
]