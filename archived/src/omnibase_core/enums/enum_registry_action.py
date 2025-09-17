from enum import Enum


# Enum for node registry actions (ONEX Standard)
class RegistryActionEnum(str, Enum):
    GET_ACTIVE_NODES = "get_active_nodes"
    GET_NODE = "get_node"
