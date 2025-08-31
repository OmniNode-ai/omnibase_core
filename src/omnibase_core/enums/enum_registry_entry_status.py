from enum import Enum


# Enum for node registry entry status values (ONEX Standard)
class RegistryEntryStatusEnum(str, Enum):
    EPHEMERAL = "ephemeral"
    ONLINE = "online"
    VALIDATED = "validated"
