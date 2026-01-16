"""Handler command type enumeration for ONEX handler operations."""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHandlerCommandType(StrValueHelper, str, Enum):
    """Handler command types for ONEX operations.

    SINGLE SOURCE OF TRUTH for typed command identifiers.
    Commands: EXECUTE, VALIDATE, DRY_RUN (simulate without side effects),
    ROLLBACK (undo), HEALTH_CHECK, DESCRIBE, CONFIGURE, RESET.
    """

    EXECUTE = "execute"
    """Execute the handler's primary operation."""

    VALIDATE = "validate"
    """Validate input data without executing the operation."""

    DRY_RUN = "dry_run"
    """Simulate execution without performing side effects."""

    ROLLBACK = "rollback"
    """Rollback or undo a previous operation."""

    HEALTH_CHECK = "health_check"
    """Check handler health and availability."""

    DESCRIBE = "describe"
    """Describe handler capabilities and metadata."""

    CONFIGURE = "configure"
    """Configure handler settings or parameters."""

    RESET = "reset"
    """Reset handler state to initial configuration."""

    @classmethod
    def values(cls) -> list[str]:
        """Return all values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling in match statements.

        Uses AssertionError instead of ModelOnexError to avoid
        circular imports in the enum module.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumHandlerCommandType"]
