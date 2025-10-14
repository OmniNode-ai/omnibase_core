from enum import Enum


# Enum for node registry execution modes (ONEX Standard)
class EnumRegistryExecutionMode(str, Enum):
    MEMORY = "memory"
    CONTAINER = "container"
    EXTERNAL = "external"
