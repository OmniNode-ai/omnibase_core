"""
Node Info CLI Command.

Command implementation for getting node information.
"""

from omnibase_core.enums.enum_cli_action import EnumCliAction
from omnibase_core.models.nodes.cli_command_base import CliCommand
from omnibase_core.models.nodes.model_cli_command_result import ModelCliCommandResult
from omnibase_core.models.nodes.model_cli_node_execution_input import (
    ModelCliNodeExecutionInput,
)


class NodeInfoCommand(CliCommand):
    """Command for getting node information."""

    def __init__(self) -> None:
        """Initialize node info command."""
        super().__init__(EnumCliAction.NODE_INFO)

    async def execute(
        self, input_data: ModelCliNodeExecutionInput
    ) -> ModelCliCommandResult:
        """Execute node info command."""
        if not self.validate_input(input_data):
            return ModelCliCommandResult.error_result(
                f"Invalid action for NodeInfoCommand: {input_data.action}"
            )

        target_node = input_data.target_node or input_data.node_name
        if not target_node:
            return ModelCliCommandResult.error_result(
                "Target node is required for node_info action"
            )

        # Implementation would go here
        result_data = {
            "node_name": target_node,
            "node_info": {},
            "metadata_included": input_data.include_metadata,
            "health_included": input_data.include_health_info,
        }

        return ModelCliCommandResult.success_result(result_data)


# Export for use
__all__ = [
    "NodeInfoCommand",
]