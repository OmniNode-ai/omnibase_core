"""
Input/Output Type Enum.

Strongly typed input/output type values for configuration.
"""

from __future__ import annotations

from enum import Enum


class EnumIOType(str, Enum):
    """Strongly typed input/output type values."""

    INPUT = "INPUT"
    OUTPUT = "output"
    CONFIGURATION = "configuration"
    METADATA = "metadata"
    PARAMETERS = "parameters"


# Export for use
__all__ = ["EnumIOType"]
