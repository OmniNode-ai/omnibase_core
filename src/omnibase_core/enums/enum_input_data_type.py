"""
Input data type enum for discriminated union.
"""

from enum import Enum


class EnumInputDataType(str, Enum):
    """Types of input data structures."""

    STRUCTURED = "structured"
    PRIMITIVE = "primitive"
    MIXED = "mixed"
