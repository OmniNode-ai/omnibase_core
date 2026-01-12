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
be satisfied by the general-purpose 6-level severity scale.

Migration Notes (OMN-1311):
- EnumValidationSeverity -> EnumSeverity (INFO, WARNING, ERROR, CRITICAL map directly)
- EnumInvariantSeverity -> EnumSeverity (subset: INFO, WARNING, CRITICAL)
- EnumViolationSeverity -> EnumSeverity (subset: INFO, WARNING, CRITICAL)
- EnumErrorSeverity -> Removed (was unused, identical values)
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumSeverity(str, Enum):
    """
    Canonical severity levels for ONEX systems.

    Standard 6-level severity scale aligned with logging conventions:
    - DEBUG: Detailed debugging information
    - INFO: Informational messages, normal operation
    - WARNING: Potential issues that should be reviewed
    - ERROR: Error conditions that need attention
    - CRITICAL: Critical conditions that must be addressed immediately
    - FATAL: Fatal errors that cause system failure

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

    FATAL = "fatal"
    """Fatal errors that cause system failure or shutdown."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @property
    def numeric_level(self) -> int:
        """
        Get numeric representation for severity comparison.

        Higher numbers indicate more severe conditions.
        Scale is compatible with Python logging levels (10, 20, 30, 40, 50, 60).
        """
        levels = {
            EnumSeverity.DEBUG: 10,
            EnumSeverity.INFO: 20,
            EnumSeverity.WARNING: 30,
            EnumSeverity.ERROR: 40,
            EnumSeverity.CRITICAL: 50,
            EnumSeverity.FATAL: 60,
        }
        return levels[self]

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
        raise ValueError(  # error-ok: simple conversion
            f"Unknown severity level: {value}"
        )


__all__ = ["EnumSeverity"]
