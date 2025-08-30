import re
from typing import Optional, Set

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError


def validate_semantic_version(version: str) -> str:
    """
    Validate that a version string follows semantic versioning format.
    Raises OnexError if invalid.
    """
    semver_pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
    if not re.match(semver_pattern, version):
        raise OnexError(
            f"Version '{version}' does not follow semantic versioning format (e.g., '1.0.0')",
            CoreErrorCode.INVALID_PARAMETER,
        )
    return version


def validate_status(value: str, allowed_statuses: Optional[Set[str]] = None) -> str:
    """
    Validate that a status value is in the allowed set. Raises OnexError if not.
    """
    if allowed_statuses is None:
        allowed_statuses = {"success", "failure", "warning"}
    if value not in allowed_statuses:
        raise OnexError(
            f"status must be one of {allowed_statuses}, got '{value}'",
            CoreErrorCode.INVALID_PARAMETER,
        )
    return value


def validate_non_empty_string(value: str, field_name: str = "field") -> str:
    """
    Validate that a string is not empty or whitespace. Raises OnexError if invalid.
    """
    if not value or not value.strip():
        raise OnexError(
            f"{field_name} cannot be empty",
            CoreErrorCode.MISSING_REQUIRED_PARAMETER,
        )
    return value.strip()
