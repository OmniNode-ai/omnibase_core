"""
Enumeration for CLI actions.

Defines all valid CLI actions that can be processed
by node_cli, replacing hardcoded string literals.
"""

from enum import Enum, unique


@unique
class EnumCliAction(Enum):
    """
    Enumeration of valid CLI actions.

    Defines all actions that can be sent to node_cli
    for processing, providing type safety and validation.
    """

    # Node operations
    GET_ACTIVE_NODES = "get_active_nodes"
    EXECUTE_NODE = "execute_node"
    NODE_INFO = "node_info"
    INTROSPECT_NODE = "introspect_node"

    # Validation and generation
    VALIDATE_NODE = "validate_node"
    GENERATE_NODE = "generate_node"
    STAMP_FILES = "stamp_files"

    # Workflow operations
    LIST_WORKFLOWS = "list_workflows"

    # Registry operations
    REGISTRY_SYNC = "registry_sync"
    REGISTRY_QUERY = "registry_query"

    # System operations
    SYSTEM_INFO = "system_info"
    SERVICE_STATUS = "service_status"

    # Documentation and help
    CONTRACT_DATA = "contract_data"
    HELP_DATA = "help_data"
