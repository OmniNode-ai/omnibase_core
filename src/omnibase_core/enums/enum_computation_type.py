"""
Computation Type Enums.

Types of computation operations for output data models.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumComputationType(StrValueHelper, str, Enum):
    """Types of computation operations."""

    NUMERIC = "numeric"
    TEXT = "text"
    BINARY = "binary"
    STRUCTURED = "structured"


__all__ = ["EnumComputationType"]
