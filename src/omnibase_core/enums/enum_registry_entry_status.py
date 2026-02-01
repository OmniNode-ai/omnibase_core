from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


# Enum for node registry entry status values (ONEX Standard)
@unique
class EnumRegistryEntryStatus(StrValueHelper, str, Enum):
    EPHEMERAL = "ephemeral"
    ONLINE = "online"
    VALIDATED = "validated"


__all__ = ["EnumRegistryEntryStatus"]
