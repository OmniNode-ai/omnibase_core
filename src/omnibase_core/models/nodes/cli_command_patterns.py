"""
CLI Command Patterns.

Command pattern implementation for CLI action handling, replacing
string-based action dispatch with type-safe command objects.

This module now imports from individual command files following
the "one model per file" principle.
"""

# Import base classes and results
from omnibase_core.models.nodes.cli_command_base import CliCommand
from omnibase_core.models.nodes.model_cli_command_result import (
    ModelCliCommandResult,
    ProtocolCliCommandResult,
)

# Import specific command implementations
from omnibase_core.models.nodes.cli_command_execute_node import ExecuteNodeCommand
from omnibase_core.models.nodes.cli_command_get_active_nodes import GetActiveNodesCommand
from omnibase_core.models.nodes.cli_command_list_nodes import ListNodesCommand
from omnibase_core.models.nodes.cli_command_node_info import NodeInfoCommand
from omnibase_core.models.nodes.cli_command_system_info import SystemInfoCommand


# Export for use
__all__ = [
    "ProtocolCliCommandResult",
    "ModelCliCommandResult",
    "CliCommand",
    "ListNodesCommand",
    "GetActiveNodesCommand",
    "ExecuteNodeCommand",
    "NodeInfoCommand",
    "SystemInfoCommand",
]