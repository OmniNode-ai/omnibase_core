"""
Get Active Nodes CLI Command.

Command implementation for getting active nodes.
"""

from omnibase_core.enums.enum_cli_action import EnumCliAction
from omnibase_core.models.nodes.cli_command_base import CliCommand
from omnibase_core.models.nodes.model_cli_command_result import ModelCliCommandResult
from omnibase_core.models.nodes.model_cli_node_execution_input import (
    ModelCliNodeExecutionInput,
)


class GetActiveNodesCommand(CliCommand):
    """Command for getting active nodes."""

    def __init__(self) -> None:
        """Initialize get active nodes command."""
        super().__init__(EnumCliAction.GET_ACTIVE_NODES)

    async def execute(
        self, input_data: ModelCliNodeExecutionInput
    ) -> ModelCliCommandResult:
        """Execute get active nodes command."""
        if not self.validate_input(input_data):
            return ModelCliCommandResult.error_result(
                f"Invalid action for GetActiveNodesCommand: {input_data.action}"
            )

        # Implementation would go here
        result_data = {
            "active_nodes": [],
            "node_count": 0,
            "health_filtered": input_data.health_filter,
        }

        return ModelCliCommandResult.success_result(result_data)


# Export for use
__all__ = [
    "GetActiveNodesCommand",
]