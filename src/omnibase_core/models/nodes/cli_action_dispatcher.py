"""
CLI Action Dispatcher.

Central dispatcher that integrates all CLI patterns including command pattern,
registry pattern, and factory pattern for comprehensive CLI action handling.
"""

from typing import Any, Dict

from omnibase_core.enums.enum_cli_action import EnumCliAction
from omnibase_core.models.nodes.model_cli_command_result import ModelCliCommandResult
from omnibase_core.models.nodes.cli_command_registry import (
    CliCommandRegistry,
    get_default_command_registry,
)
from omnibase_core.models.nodes.model_cli_node_execution_input import (
    ModelCliNodeExecutionInput,
)


class CliActionDispatcher:
    """
    Central dispatcher for CLI actions.

    Coordinates between command patterns, registry patterns, and factory patterns
    to provide a unified interface for CLI action execution.
    """

    def __init__(self, command_registry: CliCommandRegistry | None = None) -> None:
        """
        Initialize dispatcher.

        Args:
            command_registry: Command registry to use, defaults to global registry
        """
        self._command_registry = command_registry or get_default_command_registry()
        self._execution_stats: Dict[str, int] = {}

    async def dispatch(
        self, input_data: ModelCliNodeExecutionInput
    ) -> ModelCliCommandResult:
        """
        Dispatch CLI action using appropriate patterns.

        Args:
            input_data: CLI execution input

        Returns:
            Command execution result
        """
        try:
            # Validate input action
            if not input_data.validate_action():
                return ModelCliCommandResult.error_result(
                    f"Invalid or unsupported action: {input_data.action}"
                )

            # Update execution statistics
            self._update_execution_stats(input_data.action)

            # Execute using command registry
            result = await self._command_registry.execute_command(input_data)

            # Add dispatcher metadata to result
            result.result_data["dispatcher_info"] = {
                "action_validated": True,
                "registry_used": True,
                "execution_count": self._execution_stats.get(input_data.action, 0),
            }

            return result

        except Exception as e:
            return ModelCliCommandResult.error_result(
                f"Dispatcher error: {str(e)}"
            )

    def get_supported_actions(self) -> list[str]:
        """
        Get list of supported action names.

        Returns:
            List of supported CLI action strings
        """
        return self._command_registry.get_registered_action_names()

    def get_supported_action_enums(self) -> list[EnumCliAction]:
        """
        Get list of supported action enums.

        Returns:
            List of supported CLI action enums
        """
        return self._command_registry.get_registered_actions()

    def is_action_supported(self, action: str | EnumCliAction) -> bool:
        """
        Check if an action is supported.

        Args:
            action: Action string or enum

        Returns:
            True if action is supported
        """
        return self._command_registry.is_action_supported(action)

    def get_execution_stats(self) -> Dict[str, int]:
        """
        Get execution statistics by action.

        Returns:
            Dictionary mapping action names to execution counts
        """
        return self._execution_stats.copy()

    def get_dispatcher_info(self) -> Dict[str, Any]:
        """
        Get dispatcher information and status.

        Returns:
            Dispatcher information dictionary
        """
        return {
            "supported_actions": self.get_supported_actions(),
            "total_actions": len(self.get_supported_actions()),
            "execution_stats": self._execution_stats,
            "total_executions": sum(self._execution_stats.values()),
            "registry_info": {
                "type": self._command_registry.__class__.__name__,
                "registered_commands": len(self._command_registry.get_registered_actions()),
            },
        }

    def reset_stats(self) -> None:
        """Reset execution statistics."""
        self._execution_stats.clear()

    def _update_execution_stats(self, action: str) -> None:
        """
        Update execution statistics for an action.

        Args:
            action: Action name that was executed
        """
        self._execution_stats[action] = self._execution_stats.get(action, 0) + 1


# Factory is now in separate file


# Global dispatcher instance
_default_dispatcher = CliActionDispatcher()


def get_default_dispatcher() -> CliActionDispatcher:
    """
    Get the default dispatcher instance.

    Returns:
        Default CLI action dispatcher
    """
    return _default_dispatcher


async def dispatch_cli_action(
    input_data: ModelCliNodeExecutionInput,
) -> ModelCliCommandResult:
    """
    Convenience function for dispatching CLI actions.

    Args:
        input_data: CLI execution input

    Returns:
        Command execution result
    """
    return await _default_dispatcher.dispatch(input_data)


# Export for use
__all__ = [
    "CliActionDispatcher",
    "get_default_dispatcher",
    "dispatch_cli_action",
]