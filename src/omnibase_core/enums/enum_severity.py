# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Canonical severity enumeration for ONEX systems.

This is the CANONICAL severity enum for general-purpose severity classification
across the ONEX ecosystem. Use this enum for validation errors, logging context,
and any severity classification that doesn't require a specialized domain.

DOCUMENTED EXCEPTIONS (per ADR-006):
- EnumSeverityLevel: RFC 5424 syslog compatibility (11 values including EMERGENCY, ALERT, etc.)
- EnumImpactSeverity: Business impact domain (critical, high, medium, low, minimal)

These exceptions exist because they serve specific domain requirements that cannot
be satisfied by the general-purpose 5-level severity scale.

Migration Notes (OMN-1311, OMN-1296):
- EnumValidationSeverity: REMOVED - use EnumSeverity directly
- EnumInvariantSeverity: REMOVED - use EnumSeverity directly
- EnumViolationSeverity: REMOVED - use EnumSeverity directly
- EnumErrorSeverity: REMOVED (was unused, identical values)
- FATAL: REMOVED - use CRITICAL for fatal conditions
"""

from __future__ import annotations

from enum import Enum, unique

# Module-level constant for numeric severity levels (avoids per-call dict allocation)
# Scale is compatible with Python logging levels (10, 20, 30, 40, 50)
# Note: This is defined outside the enum class to avoid being treated as an enum member
_SEVERITY_LEVEL_MAP: dict[str, int] = {
    "debug": 10,
    "info": 20,
    "warning": 30,
    "error": 40,
    "critical": 50,
}


@unique
class EnumSeverity(str, Enum):
    """
    Canonical severity levels for ONEX systems.

    Standard 5-level severity scale aligned with logging conventions:
    - DEBUG: Detailed debugging information
    - INFO: Informational messages, normal operation
    - WARNING: Potential issues that should be reviewed
    - ERROR: Error conditions that need attention
    - CRITICAL: Critical conditions that must be addressed immediately

    Values are lowercase strings for consistency with logging standards.
    """

    DEBUG = "debug"
    """Detailed debugging information for development."""

    INFO = "info"
    """Informational messages indicating normal operation."""

    WARNING = "warning"
    """Potential issues that should be reviewed but don't block operation."""

    ERROR = "error"
    """Error conditions that need attention and may affect functionality."""

    CRITICAL = "critical"
    """Critical conditions that must be addressed immediately."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @property
    def numeric_level(self) -> int:
        """
        Get numeric representation for severity comparison.

        Higher numbers indicate more severe conditions.
        Scale is compatible with Python logging levels (10, 20, 30, 40, 50).

        Example:
            >>> EnumSeverity.ERROR.numeric_level
            40
        """
        return _SEVERITY_LEVEL_MAP[self.value]

    def is_error_or_above(self) -> bool:
        """Check if this is an error-level severity or higher."""
        return self.numeric_level >= 40

    def is_warning_or_above(self) -> bool:
        """Check if this is a warning-level severity or higher."""
        return self.numeric_level >= 30

    @classmethod
    def from_string(cls, value: str) -> EnumSeverity:
        """
        Convert string to severity level with case-insensitive matching.

        Args:
            value: String value to convert (case-insensitive)

        Returns:
            Matching EnumSeverity value

        Raises:
            ValueError: If no matching severity found
        """
        normalized = value.lower().strip()
        for member in cls:
            if member.value == normalized:
                return member
        # error-ok: standard Python pattern for enum string conversion
        raise ValueError(f"Unknown severity level: {value}")


__all__ = ["EnumSeverity"]
