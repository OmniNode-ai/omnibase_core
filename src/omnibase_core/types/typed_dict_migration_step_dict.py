"""
TypedDictMigrationStepDict

Type definition for migration step information.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from typing import TypedDict


class TypedDictMigrationStepDict(TypedDict, total=False):
    """Type definition for migration step information."""

    phase: str  # "preparation", "migration", "finalization"
    action: str
    description: str
    estimated_minutes: int
    # Optional fields for migration phase
    protocol: str
    source_file: str
    target_category: str
    target_path: str


__all__ = ["TypedDictMigrationStepDict"]
