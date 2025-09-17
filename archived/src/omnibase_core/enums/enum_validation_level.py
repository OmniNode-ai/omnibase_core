"""
Validation Level Enumeration for pipeline data integrity.

Defines the validation levels for pipeline data integrity checking
in the metadata processing pipeline.
"""

from enum import Enum


class EnumValidationLevel(str, Enum):
    """Validation levels for pipeline data integrity."""

    BASIC = "BASIC"
    STANDARD = "STANDARD"
    COMPREHENSIVE = "COMPREHENSIVE"
    PARANOID = "PARANOID"
