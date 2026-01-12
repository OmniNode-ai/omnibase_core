"""Node registry actions for ONEX operations."""

from enum import Enum, unique


@unique
class EnumRegistryAction(str, Enum):
    """Registry actions for node operations."""

    GET_ACTIVE_NODES = "get_active_nodes"
    GET_NODE = "get_node"
