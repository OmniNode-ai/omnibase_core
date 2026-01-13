from enum import Enum, unique


# Enum for node registry entry status values (ONEX Standard)
@unique
class EnumRegistryEntryStatus(str, Enum):
    EPHEMERAL = "ephemeral"
    ONLINE = "online"
    VALIDATED = "validated"
