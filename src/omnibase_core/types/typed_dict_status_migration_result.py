"""
TypedDict for status migration validation results.

This module defines the structure for validation results when migrating
status enums from legacy to new formats.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictStatusMigrationResult(TypedDict):
    """TypedDict for status migration validation results."""

    success: bool
    old_value: str
    old_enum: str
    new_enum: str
    migrated_value: str | None
    base_status_equivalent: str | None
    warnings: list[str]
    errors: list[str]


__all__ = [
    "TypedDictStatusMigrationResult",
]
