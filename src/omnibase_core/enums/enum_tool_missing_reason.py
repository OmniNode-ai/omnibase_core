"""Tool missing reason enumeration."""

from enum import Enum


class EnumToolMissingReason(str, Enum):
    """
    Categorized reasons for missing tools.

    Provides structured classification of why tools are missing or invalid.
    """

    NOT_FOUND = "not_found"
    TYPE_MISMATCH = "type_mismatch"
    IMPORT_ERROR = "import_error"
    DEPENDENCY_MISSING = "dependency_missing"
    CONFIGURATION_INVALID = "configuration_invalid"
    PERMISSION_DENIED = "permission_denied"
    PROTOCOL_VIOLATION = "protocol_violation"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    VERSION_INCOMPATIBLE = "version_incompatible"
    INSTANTIATION_FAILED = "instantiation_failed"
