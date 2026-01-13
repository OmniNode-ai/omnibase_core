"""
Input data type enum for discriminated union.
"""

from enum import Enum, unique


@unique
class EnumInputDataType(str, Enum):
    """Types of input data structures."""

    STRUCTURED = "structured"
    PRIMITIVE = "primitive"
    MIXED = "mixed"
