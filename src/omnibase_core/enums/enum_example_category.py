from __future__ import annotations

"""
Example Category Enum.

Strongly typed example category values for configuration.
"""


from enum import Enum, unique


@unique
class EnumExampleCategory(str, Enum):
    """Strongly typed example category values."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    VALIDATION = "validation"
    REFERENCE = "reference"


# Export for use
__all__ = ["EnumExampleCategory"]
