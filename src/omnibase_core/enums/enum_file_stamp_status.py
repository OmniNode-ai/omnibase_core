"""File stamp status indicators for validation."""

from enum import Enum, unique


@unique
class EnumFileStampStatus(Enum):
    """File stamp status indicators."""

    VALID = "VALID"
    INVALID = "INVALID"
    MISSING = "MISSING"
    EXPIRED = "EXPIRED"
    CORRUPTED = "CORRUPTED"
