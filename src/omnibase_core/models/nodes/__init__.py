"""
ONEX Nodes Domain Models.

Centralized collection of all node-related models in the ONEX ecosystem.
Follows domain-driven design principles for better organization.
"""

# Node execution and CLI models
from .model_cli_node_execution_input import ModelCliNodeExecutionInput

# Node metadata and collections
from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
from .model_metadata_node_collection import ModelMetadataNodeCollection
from .model_metadata_node_info import ModelMetadataNodeInfo

# Metadata node enums and supporting models
from .enum_metadata_node_complexity import ModelMetadataNodeComplexity
from .enum_metadata_node_status import ModelMetadataNodeStatus
from .enum_metadata_node_type import ModelMetadataNodeType
from .model_metadata_usage_metrics import ModelMetadataUsageMetrics

# CLI command patterns and components
from .cli_command_base import CliCommand
from .model_cli_command_result import (
    ModelCliCommandResult,
    ProtocolCliCommandResult,
)
from .cli_command_execute_node import ExecuteNodeCommand
from .cli_command_get_active_nodes import GetActiveNodesCommand
from .cli_command_list_nodes import ListNodesCommand
from .cli_command_node_info import NodeInfoCommand
from .cli_command_system_info import SystemInfoCommand

# CLI action dispatchers
from .cli_action_dispatcher import CliActionDispatcher
from .cli_action_dispatcher_factory import CliActionDispatcherFactory

# Node capability and information models
from .model_node_capability import ModelNodeCapability
from .model_node_information import ModelNodeInformation
from .model_node_type import ModelNodeType

__all__ = [
    # CLI and execution
    "ModelCliNodeExecutionInput",
    # Metadata and collections
    "ModelMetadataNodeAnalytics",
    "ModelMetadataNodeCollection",
    "ModelMetadataNodeComplexity",
    "ModelMetadataNodeInfo",
    "ModelMetadataNodeStatus",
    "ModelMetadataNodeType",
    "ModelMetadataUsageMetrics",
    # CLI command patterns and components
    "CliCommand",
    "ModelCliCommandResult",
    "ProtocolCliCommandResult",
    "ExecuteNodeCommand",
    "GetActiveNodesCommand",
    "ListNodesCommand",
    "NodeInfoCommand",
    "SystemInfoCommand",
    # CLI action dispatchers
    "CliActionDispatcher",
    "CliActionDispatcherFactory",
    # Node capabilities and information
    "ModelNodeCapability",
    "ModelNodeInformation",
    "ModelNodeType",
]