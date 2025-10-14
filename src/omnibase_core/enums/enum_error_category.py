"""
Error categorization enum for task queue operations.

Categorizes errors by type to enable appropriate retry and recovery strategies.
"""

from enum import Enum


class EnumErrorCategory(str, Enum):
    """Error categories for task queue operations."""

    TRANSIENT = "transient"
    CONFIGURATION = "configuration"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    VALIDATION = "validation"
    SYSTEM = "system"
    UNKNOWN = "unknown"
