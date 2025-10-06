from __future__ import annotations

from typing import Dict, TypedDict

"""
Validation result model for status migration operations.

This module defines the structure for validation results when migrating
status enums from legacy to new formats.
"""


from typing import TypedDict


class ValidationResult(TypedDict):
    """Typed dictionary for migration validation results."""

    success: bool
    old_value: str
    old_enum: str
    new_enum: str
    migrated_value: str | None
    base_status_equivalent: str | None
    warnings: list[str]
    errors: list[str]


# Export for use
__all__ = [
    "ValidationResult",
]
