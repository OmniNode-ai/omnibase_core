#!/usr/bin/env python3
"""
Validation-related enums for ONEX validation systems.

Defines error severity levels, validation modes, and validation levels
for ONEX validation and error handling systems.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumErrorSeverity(Enum):
    """
    Severity levels for validation errors and system errors.

    Used to categorize the impact and urgency of different types of errors.
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


@unique
class EnumValidationLevel(StrValueHelper, str, Enum):
    """
    Validation levels for pipeline data integrity.

    Defines the validation levels for pipeline data integrity checking
    in the metadata processing pipeline.
    """

    BASIC = "BASIC"
    STANDARD = "STANDARD"
    COMPREHENSIVE = "COMPREHENSIVE"
    PARANOID = "PARANOID"
