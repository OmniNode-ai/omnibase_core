"""
Base CLI Command Classes.

Abstract base command class and core command functionality.
"""

from abc import ABC, abstractmethod

from omnibase_core.enums.enum_cli_action import EnumCliAction
from omnibase_core.models.nodes.model_cli_command_result import ModelCliCommandResult
from omnibase_core.models.nodes.model_cli_node_execution_input import (
    ModelCliNodeExecutionInput,
)


class CliCommand(ABC):
    """Abstract base class for CLI commands."""

    def __init__(self, action: EnumCliAction) -> None:
        """Initialize command with action type."""
        self.action = action

    @abstractmethod
    async def execute(
        self, input_data: ModelCliNodeExecutionInput
    ) -> ModelCliCommandResult:
        """
        Execute the command with the given input.

        Args:
            input_data: CLI execution input parameters

        Returns:
            Command execution result
        """
        pass

    @property
    def command_name(self) -> str:
        """Get command name for identification."""
        return self.action.value

    def validate_input(self, input_data: ModelCliNodeExecutionInput) -> bool:
        """
        Validate input data for this command.

        Args:
            input_data: Input data to validate

        Returns:
            True if input is valid for this command
        """
        return input_data.action == self.action.value


# Export for use
__all__ = [
    "CliCommand",
]