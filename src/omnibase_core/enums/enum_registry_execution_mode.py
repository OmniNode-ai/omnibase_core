from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


# Enum for node registry execution modes (ONEX Standard)
@unique
class EnumRegistryExecutionMode(StrValueHelper, str, Enum):
    MEMORY = "memory"
    CONTAINER = "container"
    EXTERNAL = "external"


__all__ = ["EnumRegistryExecutionMode"]
