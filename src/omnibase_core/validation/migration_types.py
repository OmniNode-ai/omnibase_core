from typing import Dict, TypedDict

"""
Migration type definitions for protocol migration operations.
"""

# Import all TypedDict classes from their individual files
from .typed_dict_migration_conflict_base_dict import TypedDictMigrationConflictBaseDict
from .typed_dict_migration_duplicate_conflict_dict import (
    TypedDictMigrationDuplicateConflictDict,
)
from .typed_dict_migration_name_conflict_dict import TypedDictMigrationNameConflictDict
from .typed_dict_migration_step_dict import TypedDictMigrationStepDict

# Export all types
__all__ = [
    "TypedDictMigrationConflictBaseDict",
    "TypedDictMigrationDuplicateConflictDict",
    "TypedDictMigrationNameConflictDict",
    "TypedDictMigrationStepDict",
]
