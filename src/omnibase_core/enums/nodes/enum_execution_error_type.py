"""
Execution error type enumeration.

Provides strongly typed error classifications for node execution failures.
"""

from enum import Enum


class EnumExecutionErrorType(str, Enum):
    """Type of execution error."""

    VALIDATION_ERROR = "validation_error"
    CONFIGURATION_ERROR = "configuration_error"
    DEPENDENCY_ERROR = "dependency_error"
    PERMISSION_ERROR = "permission_error"
    RESOURCE_ERROR = "resource_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    INTERNAL_ERROR = "internal_error"
    USER_ERROR = "user_error"
    SYSTEM_ERROR = "system_error"
