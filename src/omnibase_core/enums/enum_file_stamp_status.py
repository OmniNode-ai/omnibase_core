# Generated from contract: file_stamps_contract.yaml
from enum import Enum, unique


@unique
class EnumFileStampStatus(Enum):
    """File stamp status indicators."""

    VALID = "VALID"
    INVALID = "INVALID"
    MISSING = "MISSING"
    EXPIRED = "EXPIRED"
    CORRUPTED = "CORRUPTED"
