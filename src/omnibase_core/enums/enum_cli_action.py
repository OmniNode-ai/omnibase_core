"""
CLI Action Enum.

Strongly typed action values for CLI operations, replacing string-based
action dispatch with type-safe enum dispatch patterns.
"""

from enum import Enum


class EnumCliAction(str, Enum):
    """Strongly typed action values for CLI operations."""

    # Node operations
    GET_ACTIVE_NODES = "get_active_nodes"
    LIST_NODES = "list_nodes"
    EXECUTE_NODE = "execute_node"
    NODE_INFO = "node_info"
    INTROSPECT_NODE = "introspect_node"

    # Validation and generation
    VALIDATE_NODE = "validate_node"
    GENERATE_NODE = "generate_node"
    STAMP_FILES = "stamp_files"

    # Workflow operations
    LIST_WORKFLOWS = "list_workflows"
    EXECUTE_WORKFLOW = "execute_workflow"

    # Registry operations
    REGISTRY_SYNC = "registry_sync"
    REGISTRY_QUERY = "registry_query"

    # System operations
    SYSTEM_INFO = "system_info"
    SERVICE_STATUS = "service_status"
    HEALTH_CHECK = "health_check"

    # Documentation and help
    CONTRACT_DATA = "contract_data"
    HELP_DATA = "help_data"

    # Service management
    START_SERVICE = "start_service"
    STOP_SERVICE = "stop_service"
    RESTART_SERVICE = "restart_service"


# Export for use
__all__ = ["EnumCliAction"]