from enum import Enum, unique


# Enum for node registry execution modes (ONEX Standard)
@unique
class EnumRegistryExecutionMode(str, Enum):
    MEMORY = "memory"
    CONTAINER = "container"
    EXTERNAL = "external"
