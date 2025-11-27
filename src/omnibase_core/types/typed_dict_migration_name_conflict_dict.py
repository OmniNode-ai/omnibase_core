"""
TypedDict for migration name conflict data.

Strongly-typed representation for name conflict information.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from .typed_dict_migration_conflict_base_dict import TypedDictMigrationConflictBaseDict


class TypedDictMigrationNameConflictDict(TypedDictMigrationConflictBaseDict):
    """Strongly-typed definition for name conflict information."""

    source_signature: str
    spi_signature: str


__all__ = ["TypedDictMigrationNameConflictDict"]
