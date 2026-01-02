from __future__ import annotations

"""
Invariant severity enumeration for user-defined validation rules.

Defines the severity levels for invariant validation failures,
determining how the system responds to failed checks.
"""


from enum import Enum, unique


@unique
class EnumInvariantSeverity(str, Enum):
    """Severity levels for invariant validation failures."""

    CRITICAL = "critical"
    """Must pass or deployment fails."""

    WARNING = "warning"
    """Should pass, logged if fails."""

    INFO = "info"
    """Informational, always logged."""


__all__ = ["EnumInvariantSeverity"]
