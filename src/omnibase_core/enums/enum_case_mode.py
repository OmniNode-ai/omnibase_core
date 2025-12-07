"""
Case transformation modes for contract-driven NodeCompute.

This module defines the case modes available for CASE_CONVERSION transformations.
"""

from enum import Enum


class EnumCaseMode(str, Enum):
    """
    Case transformation modes.

    Attributes:
        UPPER: Convert text to uppercase.
        LOWER: Convert text to lowercase.
        TITLE: Convert text to titlecase.
    """

    UPPER = "uppercase"
    LOWER = "lowercase"
    TITLE = "titlecase"
