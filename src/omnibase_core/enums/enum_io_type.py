from __future__ import annotations

"""
Input/Output Type Enum.

Strongly typed input/output type values for configuration.
"""


from enum import Enum, unique


@unique
class EnumIoType(str, Enum):
    """Strongly typed input/output type values."""

    INPUT = "input"
    OUTPUT = "output"
    CONFIGURATION = "configuration"
    METADATA = "metadata"
    PARAMETERS = "parameters"


# Export for use
__all__ = ["EnumIoType"]
