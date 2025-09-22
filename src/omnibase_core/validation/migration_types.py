"""
Migration type definitions for protocol migration operations.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictMigrationConflictBaseDict(TypedDict):
    """Base type definition for migration conflict information."""

    type: str
    protocol_name: str
    source_file: str
    spi_file: str
    recommendation: str


class TypedDictMigrationNameConflictDict(TypedDictMigrationConflictBaseDict):
    """Type definition for name conflict information."""

    source_signature: str
    spi_signature: str


class TypedDictMigrationDuplicateConflictDict(TypedDictMigrationConflictBaseDict):
    """Type definition for exact duplicate conflict information."""

    signature_hash: str


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


# Export all types
__all__ = [
    "TypedDictMigrationConflictBaseDict",
    "TypedDictMigrationNameConflictDict",
    "TypedDictMigrationDuplicateConflictDict",
    "TypedDictMigrationStepDict",
]
