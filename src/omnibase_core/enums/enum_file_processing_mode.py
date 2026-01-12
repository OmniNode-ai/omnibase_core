"""File processing modes for stamp operations."""

from enum import Enum, unique


@unique
class EnumFileProcessingMode(Enum):
    """File processing modes for stamp operations."""

    FAST = "FAST"
    STANDARD = "STANDARD"
    COMPREHENSIVE = "COMPREHENSIVE"
