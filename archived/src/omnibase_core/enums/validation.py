#!/usr/bin/env python3
"""
Validation-related enums for ONEX validation systems.

Defines error severity levels, validation modes, and validation levels
for ONEX validation and error handling systems.
"""

from enum import Enum


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


class EnumValidationMode(Enum):
    """
    Validation modes for tool testing and validation operations.

    Enumeration of validation modes for different testing scenarios.
    """

    STRICT = "strict"
    LENIENT = "lenient"
    SMOKE = "smoke"
    REGRESSION = "regression"
    INTEGRATION = "integration"
