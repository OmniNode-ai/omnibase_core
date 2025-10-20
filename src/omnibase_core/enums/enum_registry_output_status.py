from enum import Enum


# Enum for node registry output status values (ONEX Standard)
class EnumRegistryOutputStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"
