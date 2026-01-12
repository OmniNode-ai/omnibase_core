from enum import Enum, unique


# Enum for node registry actions (ONEX Standard)
@unique
class EnumRegistryAction(str, Enum):
    GET_ACTIVE_NODES = "get_active_nodes"
    GET_NODE = "get_node"
