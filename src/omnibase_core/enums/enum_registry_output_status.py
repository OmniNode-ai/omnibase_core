from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


# Enum for node registry output status values (ONEX Standard)
@unique
class EnumRegistryOutputStatus(StrValueHelper, str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"


__all__ = ["EnumRegistryOutputStatus"]
