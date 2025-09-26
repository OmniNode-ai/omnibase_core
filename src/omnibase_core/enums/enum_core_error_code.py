"""
ONEX Core Error Codes

Standardized error codes for the ONEX framework.
"""

from enum import Enum, unique


@unique
class EnumCoreErrorCode(str, Enum):
    """Core error codes for ONEX system."""

    VALIDATION_ERROR = "validation_error"
    OPERATION_FAILED = "operation_failed"
    NOT_FOUND = "not_found"
    CONFIGURATION_ERROR = "configuration_error"
    DEPENDENCY_ERROR = "dependency_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    PERMISSION_ERROR = "permission_error"
    RESOURCE_ERROR = "resource_error"
    INTERNAL_ERROR = "internal_error"
    CONVERSION_ERROR = "conversion_error"


__all__ = ["EnumCoreErrorCode"]
