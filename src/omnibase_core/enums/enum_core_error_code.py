#!/usr/bin/env python3
"""
ONEX Core Error Codes

Standardized error codes for the ONEX framework.
"""

from enum import Enum


class EnumCoreErrorCode(str, Enum):
    """Core error codes for ONEX system."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    OPERATION_FAILED = "OPERATION_FAILED"
    NOT_FOUND = "NOT_FOUND"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    RESOURCE_ERROR = "RESOURCE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
