"""
Computation Type Enums.

Types of computation operations for output data models.
"""

from enum import Enum


class EnumComputationType(str, Enum):
    """Types of computation operations."""

    NUMERIC = "numeric"
    TEXT = "text"
    BINARY = "binary"
    STRUCTURED = "structured"
