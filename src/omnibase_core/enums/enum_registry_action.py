"""Node registry actions for ONEX operations."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRegistryAction(StrValueHelper, str, Enum):
    """Registry actions for node operations."""

    GET_ACTIVE_NODES = "get_active_nodes"
    GET_NODE = "get_node"
