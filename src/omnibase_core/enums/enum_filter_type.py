"""Filter type enumeration for strongly typed filtering."""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumFilterType(str, Enum):
    """Strongly typed filter type values."""

    STRING = "string"
    NUMERIC = "numeric"
    DATETIME = "datetime"
    LIST = "list"
    METADATA = "metadata"
    STATUS = "status"
    COMPLEX = "complex"


# Export for use
__all__ = ["EnumFilterType"]
