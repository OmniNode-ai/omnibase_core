from __future__ import annotations

"""
Migration Conflict Type Enum.

Strongly typed enumeration for migration conflict type discriminators.
"""

from enum import Enum, unique


@unique
class EnumMigrationConflictType(str, Enum):
    """Strongly typed migration conflict type discriminators.

    Used for discriminated union patterns in migration conflict handling.
    Replaces Union[TypedDictMigrationDuplicateConflictDict,
    TypedDictMigrationNameConflictDict] patterns with structured conflict handling.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    NAME_CONFLICT = "name_conflict"
    EXACT_DUPLICATE = "exact_duplicate"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_name_conflict(cls, conflict_type: EnumMigrationConflictType) -> bool:
        """Check if the conflict type represents a name conflict."""
        return conflict_type == cls.NAME_CONFLICT

    @classmethod
    def is_exact_duplicate(cls, conflict_type: EnumMigrationConflictType) -> bool:
        """Check if the conflict type represents an exact duplicate."""
        return conflict_type == cls.EXACT_DUPLICATE

    @classmethod
    def is_resolvable_conflict(cls, conflict_type: EnumMigrationConflictType) -> bool:
        """Check if the conflict type is typically resolvable."""
        # Name conflicts can often be resolved by renaming
        return conflict_type == cls.NAME_CONFLICT

    @classmethod
    def requires_manual_resolution(
        cls, conflict_type: EnumMigrationConflictType
    ) -> bool:
        """Check if the conflict type requires manual resolution."""
        # Exact duplicates might be automatically resolvable by deduplication
        return conflict_type == cls.NAME_CONFLICT

    @classmethod
    def get_all_conflict_types(cls) -> list[EnumMigrationConflictType]:
        """Get all migration conflict types."""
        return [cls.NAME_CONFLICT, cls.EXACT_DUPLICATE]


# Export for use
__all__ = ["EnumMigrationConflictType"]
