"""
TypedDict definition for error status summary.

Strongly-typed structure for error status summary methods.
"""

from typing import TypedDict


class TypedDictErrorSummary(TypedDict):
    """Typed structure for error status summary."""

    status_type: str
    error_code: str
    error_message: str
    has_recovery_suggestion: bool
    recovery_suggestion: str | None
    is_critical: bool
    severity: str


__all__ = [
    "TypedDictErrorSummary",
]
