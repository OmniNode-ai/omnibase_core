from typing import Dict, TypedDict

"""
Migration type definitions for protocol migration operations.
"""

# Import from types module (ONEX pattern: TypedDicts in types/)
from omnibase_core.types.typed_dict_migration_step_dict import (
    TypedDictMigrationStepDict,
)

# Import all TypedDict classes from their individual files
from .typed_dict_migration_conflict_base_dict import TypedDictMigrationConflictBaseDict
from .typed_dict_migration_duplicate_conflict_dict import (
    TypedDictMigrationDuplicateConflictDict,
)
from .typed_dict_migration_name_conflict_dict import TypedDictMigrationNameConflictDict

# Export all types
__all__ = [
    "TypedDictMigrationConflictBaseDict",
    "TypedDictMigrationDuplicateConflictDict",
    "TypedDictMigrationNameConflictDict",
    "TypedDictMigrationStepDict",
]
