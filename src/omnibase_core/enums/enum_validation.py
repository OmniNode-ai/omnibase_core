#!/usr/bin/env python3
"""
Validation-related enums for ONEX validation systems.

Defines validation levels for ONEX validation and error handling systems.
"""

from enum import Enum, unique


@unique
class EnumValidationLevel(str, Enum):
    """
    Validation levels for pipeline data integrity.

    Defines the validation levels for pipeline data integrity checking
    in the metadata processing pipeline.
    """

    BASIC = "BASIC"
    STANDARD = "STANDARD"
    COMPREHENSIVE = "COMPREHENSIVE"
    PARANOID = "PARANOID"
