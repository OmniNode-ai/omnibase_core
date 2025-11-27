"""
TypedDict for migration duplicate conflict data.

Strongly-typed representation for exact duplicate conflict information.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from .typed_dict_migration_conflict_base_dict import TypedDictMigrationConflictBaseDict


class TypedDictMigrationDuplicateConflictDict(TypedDictMigrationConflictBaseDict):
    """Strongly-typed definition for exact duplicate conflict information."""

    signature_hash: str


__all__ = ["TypedDictMigrationDuplicateConflictDict"]
