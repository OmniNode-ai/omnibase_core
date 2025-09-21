"""
Security level enumeration for CLI operations.

Defines the different security levels for CLI execution.
Follows ONEX one-enum-per-file naming conventions.
"""

from __future__ import annotations

from enum import Enum


class EnumSecurityLevel(str, Enum):
    """
    Strongly typed security level for CLI operations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    MINIMAL = "minimal"  # Minimal security restrictions
    STANDARD = "standard"  # Standard security restrictions
    STRICT = "strict"  # Strict security restrictions

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def get_security_order(cls) -> list[EnumSecurityLevel]:
        """Get security levels in order of increasing security."""
        return [cls.MINIMAL, cls.STANDARD, cls.STRICT]

    def is_more_secure_than(self, other: EnumSecurityLevel) -> bool:
        """Check if this level is more secure than another level."""
        order = self.get_security_order()
        return order.index(self) > order.index(other)

    def allows_level(self, other: EnumSecurityLevel) -> bool:
        """Check if this level allows operations from another level."""
        if self == other:
            return True
        return self.is_more_secure_than(other)

    @classmethod
    def is_sandbox_required(cls, level: EnumSecurityLevel) -> bool:
        """Check if sandboxed execution is required for this security level."""
        return level in {cls.STRICT}

    @classmethod
    def is_audit_required(cls, level: EnumSecurityLevel) -> bool:
        """Check if audit logging is required for this security level."""
        return level in {cls.STANDARD, cls.STRICT}


# Export for use
__all__ = ["EnumSecurityLevel"]