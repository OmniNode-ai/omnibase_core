# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Handler Command Type Enumeration.

Typed command identifiers for handler operations.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn


@unique
class EnumHandlerCommandType(str, Enum):
    """
    Enumeration of handler command types.

    SINGLE SOURCE OF TRUTH for typed handler command identifiers.
    Replaces magic strings in handler command dispatching.

    Using an enum instead of raw strings:
    - Prevents typos ("execute" vs "Execute")
    - Enables IDE autocompletion
    - Provides exhaustiveness checking
    - Centralizes command type definitions
    - Preserves full type safety

    Command Types:
        EXECUTE: Primary handler execution
        VALIDATE: Input validation only
        DRY_RUN: Simulated execution
        ROLLBACK: Undo previous operation
        HEALTH_CHECK: Handler health check
        DESCRIBE: Describe handler metadata
        CONFIGURE: Configure handler settings
        RESET: Reset handler state

    Example:
        >>> from omnibase_core.enums import EnumHandlerCommandType
        >>> cmd = EnumHandlerCommandType.EXECUTE
        >>> str(cmd)
        'execute'
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

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def values(cls) -> list[str]:
        """Return all values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling in match statements."""
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumHandlerCommandType"]
