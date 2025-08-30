from enum import Enum


# Enum for node registry execution modes (ONEX Standard)
class RegistryExecutionModeEnum(str, Enum):
    MEMORY = "memory"
    CONTAINER = "container"
    EXTERNAL = "external"
