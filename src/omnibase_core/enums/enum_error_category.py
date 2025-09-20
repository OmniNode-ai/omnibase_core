"""
Error categorization enum for ONEX operations.

Categorizes errors by type to enable appropriate retry and recovery strategies.
"""

from enum import Enum


class EnumErrorCategory(str, Enum):
    """Error categories for ONEX operations."""

    # Transient errors that can be retried
    TRANSIENT = "transient"

    # Configuration or setup errors
    CONFIGURATION = "configuration"

    # Resource exhaustion errors
    RESOURCE_EXHAUSTION = "resource_exhaustion"

    # Authentication and authorization errors
    AUTHENTICATION = "authentication"

    # Network-related errors
    NETWORK = "network"

    # Data validation errors
    VALIDATION = "validation"

    # File system and I/O errors
    FILE_SYSTEM = "file_system"

    # Business logic errors
    BUSINESS_LOGIC = "business_logic"

    # External service errors
    EXTERNAL_SERVICE = "external_service"

    # Database errors
    DATABASE = "database"

    # System-level errors
    SYSTEM = "system"

    # Unknown or unclassified errors
    UNKNOWN = "unknown"