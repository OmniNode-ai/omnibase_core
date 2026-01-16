"""
Validation Mode Enum.

Defines validation behavior modes for controlling strictness in validation operations.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumValidationMode(StrValueHelper, str, Enum):
    """
    Validation mode controlling how strictly validation rules are enforced.

    This enum provides two modes for validation behavior:
    - STRICT: All validation rules must pass; any failure stops processing.
    - PERMISSIVE: Validation issues are logged but processing continues.

    Use STRICT mode for production environments where data integrity is critical.
    Use PERMISSIVE mode for development, migration, or debugging scenarios where
    you need to inspect all issues rather than failing on the first one.

    Example:
        >>> mode = EnumValidationMode.STRICT
        >>> mode.is_strict()
        True

        >>> mode = EnumValidationMode.PERMISSIVE
        >>> mode.allows_continuation()
        True

        >>> # String coercion for Pydantic
        >>> from pydantic import BaseModel
        >>> class Config(BaseModel):
        ...     mode: EnumValidationMode
        >>> config = Config(mode="strict")
        >>> config.mode == EnumValidationMode.STRICT
        True
    """

    STRICT = "strict"
    """
    Strict validation mode.

    All validation rules must pass. Any validation failure immediately
    stops processing and raises an error. Use for production environments
    where data integrity is critical.
    """

    PERMISSIVE = "permissive"
    """
    Permissive validation mode.

    Validation issues are collected and logged but do not stop processing.
    Use for development, migration, or debugging scenarios where you need
    to see all validation issues rather than failing on the first one.
    """

    def is_strict(self) -> bool:
        """
        Check if this mode enforces strict validation.

        Returns:
            True if validation failures should stop processing.
        """
        return self == EnumValidationMode.STRICT

    def allows_continuation(self) -> bool:
        """
        Check if this mode allows processing to continue despite validation issues.

        Returns:
            True if processing can continue after validation issues.
        """
        return self == EnumValidationMode.PERMISSIVE


__all__ = ["EnumValidationMode"]
