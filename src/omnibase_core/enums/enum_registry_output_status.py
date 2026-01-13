from enum import Enum, unique


# Enum for node registry output status values (ONEX Standard)
@unique
class EnumRegistryOutputStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"
